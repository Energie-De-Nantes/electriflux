import os
import zipfile
import logging
import paramiko
import tempfile
import functools
import pandas as pd

from pathlib import Path
from Crypto.Cipher import AES

from typing import Callable

import logging
logger = logging.getLogger(__name__)

def decrypt_file(file_path: Path, key: bytes, iv: bytes, prefix: str="decrypted_") -> Path:
    if file_path.stem.startswith(prefix):
        return file_path
    
    # Initialize the AES cipher with CBC mode
    cipher = AES.new(key, AES.MODE_CBC, iv)
    output_file = file_path.with_name(prefix + file_path.stem + ".zip")
    # Decrypt the input file and write the decrypted content to the output file
    with file_path.open("rb") as f_in, output_file.open("wb") as f_out:
        decrypted_data = cipher.decrypt(f_in.read())
        f_out.write(decrypted_data)
    return output_file

def encrypt_file(file_path: Path, key: bytes, iv: bytes, prefix: str="encrypted_") -> Path:
    if prefix in file_path.stem:
        return file_path
    # Initialize the AES cipher with CBC mode
    cipher = AES.new(key, AES.MODE_CBC, iv)
    output_file = file_path.with_name(prefix + file_path.stem + ".enc")
    # Encrypt the input file and write the encrypted content to the output file
    with file_path.open("rb") as f_in, output_file.open("wb") as f_out:
        while True:
            data = f_in.read(16)
            if len(data) == 0:
                break
            elif len(data) % 16!= 0:
                data += b' ' * (16 - len(data) % 16)
            encrypted_data = cipher.encrypt(data)
            f_out.write(encrypted_data)
    return output_file

def download_decrypt_extract(sftp: paramiko.SFTPClient, remote_file: str, output_path: Path, key: bytes, iv: bytes) -> bool:
    """
    Downloads a file from SFTP, decrypts it using decrypt_file, extracts its contents, and cleans up temporary files.

    Args:
    sftp (paramiko.SFTPClient): An active SFTP client connection.
    remote_file (str): Path to the file on the remote server.
    output_path (Path): Local path where extracted contents should be saved.
    key (bytes): 16-byte key for AES decryption.
    iv (bytes): 16-byte initialization vector for AES decryption.

    Returns:
    bool: True if successful, False otherwise.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        try:
            # Download file
            local_encrypted_path = Path(temp_dir) / Path(remote_file).name
            sftp.get(remote_file, str(local_encrypted_path))

            # Decrypt file using decrypt_file function
            decrypted_path = decrypt_file(local_encrypted_path, key, iv)

            # Extract contents
            with zipfile.ZipFile(decrypted_path, 'r') as zip_ref:
                zip_ref.extractall(output_path)

            logger.debug(f"Successfully processed {remote_file}")
            return True

        except paramiko.SSHException as e:
            logger.error(f"SFTP error while downloading {remote_file}: {str(e)}")
        except ValueError as e:
            logger.error(f"Decryption error for {remote_file}: {str(e)}")
        except zipfile.BadZipFile as e:
            logger.error(f"ZIP extraction error for {remote_file}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error processing {remote_file}: {str(e)}")

        return False

def check_required(required_keys: list[str]):
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(config: dict[str, str], *args, **kwargs):
            missing_keys = [key for key in required_keys if key not in config]
            if missing_keys:
                raise ValueError(f"Missing required keys in config: {', '.join(missing_keys)}")
            return func(config, *args, **kwargs)
        return wrapper
    return decorator

@check_required(['FTP_ADDRESS', 'FTP_USER', 'FTP_PASSWORD', 'AES_KEY', 'AES_IV'])
def download_decrypt_extract_new_files(
    config: dict[str, str], 
    tasks: list[str], 
    local: Path,
    force: bool = False,
    callback: Callable[[str, int, int, str], None] | None = None
) -> list[tuple[str, str]]:
    """
    Downloads, decrypts, and extracts new files from the SFTP server, skipping files that have already been processed.
    Uses a callback function for progress tracking.

    Parameters:
    config (dict[str, str]): Configuration dictionary containing SFTP details, key, and IV.
    tasks (list[str]): List of directory types to process (e.g., ['R15', 'C15']).
    local (Path): The local root path to save extracted files.
    callback (callable, optional): A function to call for progress updates. It should accept the following parameters:
                                   - task_type (str): The current task type being processed.
                                   - total_files (int): Total number of files to process.
                                   - current_file (int): Current file being processed (1-indexed).
                                   - file_name (str): Name of the current file being processed.

    Returns:
    list[tuple[str, str]]: A list of tuples containing (zip_name, task_type) of newly processed files.
    """

    key = bytes.fromhex(config['AES_KEY'])
    iv = bytes.fromhex(config['AES_IV'])

    csv_path = local / "processed_zips.csv"
    if force and csv_path.exists():
        csv_path.unlink()
    
    if csv_path.exists():
        df = pd.read_csv(csv_path)
        processed_zips = set(df['zip_name'])
    else:
        df = pd.DataFrame(columns=['zip_name', 'flux'])
        processed_zips = set()

    transport = paramiko.Transport((config['FTP_ADDRESS'], 22))
    transport.connect(username=config['FTP_USER'], password=config['FTP_PASSWORD'])
    sftp = paramiko.SFTPClient.from_transport(transport)

    newly_processed_files = []

    try:
        for task_type in tasks:
            distant = '/flux_enedis/' + str(config[f'FTP_{task_type}_DIR'])
            local_dir = local.joinpath(task_type)
            local_dir.mkdir(parents=True, exist_ok=True)

            try:
                files_to_process = [f for f in sftp.listdir(distant) if f not in processed_zips]
                total_files = len(files_to_process)

                for index, file_name in enumerate(files_to_process, start=1):
                    if callback:
                        callback(task_type, total_files, index, file_name)

                    remote_file_path = os.path.join(distant, file_name)
                    output_path = local_dir / file_name.replace('.zip', '')
                    
                    success = download_decrypt_extract(sftp, remote_file_path, output_path, key, iv)
                    
                    if success:
                        newly_processed_files.append((file_name, task_type))
                        df = pd.concat([df, pd.DataFrame({'zip_name': [file_name], 'flux': [task_type]})], ignore_index=True)

            except Exception as e:
                logger.error(f"Failed to process files from {distant}: {e}")

    finally:
        sftp.close()
        transport.close()

    df.to_csv(csv_path, index=False)

    return newly_processed_files

