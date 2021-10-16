import argparse
import hashlib
import logging
import os
from collections import defaultdict


def chunk_reader(fd, chunk_size):
    """Generator that reads a file in chunks of bytes"""
    while True:
        chunk = fd.read(chunk_size)
        if not chunk:
            return
        yield chunk


def get_hash(filename, chunk_size, first_chunk_only=False, hash=hashlib.sha1):
    hashobj = hash()
    file_object = open(filename, 'rb')

    if first_chunk_only:
        hashobj.update(file_object.read(chunk_size))
    else:
        for chunk in chunk_reader(file_object, chunk_size):
            hashobj.update(chunk)
    file_hash = hashobj.digest()

    file_object.close()
    return file_hash


def check_for_duplicates(path, chunk_size, recursive, hash=hashlib.sha1):
    hashes_by_size = defaultdict(list)  # dict of size_in_bytes: [full_path_to_file1, full_path_to_file2, ]
    hashes_on_1k = defaultdict(list)  # dict of (hash1k, size_in_bytes): [full_path_to_file1, full_path_to_file2, ]
    hashes_full = {}   # dict of full_file_hash: full_path_to_file_string
    duplicates = defaultdict(set)

    logger.info('Comparing file sizes')

    if not recursive:
        for filename in os.listdir(path):
            try:
                full_path = os.path.realpath(os.path.join(path, filename))
                file_size = os.path.getsize(full_path)
                hashes_by_size[file_size].append(full_path)
            except (OSError,):
                    # not accessible (permissions, etc) - pass on
                    logger.warning(f'Error reading file: {os.path.join(dirpath, filename)}')
                    continue
    else: 
        for dirpath, dirnames, filenames in os.walk(path):
            # get all files that have the same size - they are the collision candidates
            for filename in filenames:
                full_path = os.path.join(dirpath, filename)
                try:
                    # if the target is a symlink (soft one), this will 
                    # dereference it - change the value to the actual target file
                    full_path = os.path.realpath(full_path)
                    file_size = os.path.getsize(full_path)
                    hashes_by_size[file_size].append(full_path)
                except (OSError,):
                    # not accessible (permissions, etc) - pass on
                    logger.warning(f'Error reading file: {os.path.join(dirpath, filename)}')
                    continue

    logger.info('Comparing short hashes')

    # For all files with the same file size, get their hash on the 1st chunk only
    for size_in_bytes, files in hashes_by_size.items():
        if len(files) < 2:
            continue    # this file size is unique, no need to spend CPU cycles on it

        for filename in files:
            try:
                small_hash = get_hash(filename, chunk_size, first_chunk_only=True)
                # the key is the hash on the first chunk plus the size - to
                # avoid collisions on equal hashes in the first part of the file
                # credits to @Futal for the optimization
                hashes_on_1k[(small_hash, size_in_bytes)].append(filename)
            except (OSError,):
                # the file access might've changed till the exec point got here 
                logger.warning(f'Error reading file: {os.path.join(dirpath, filename)}')
                continue

    logger.info('Comparing full hashes')

    # For all files with the same hash on the 1st chunk, get their hash on the full file - collisions will be duplicates
    for __, files_list in hashes_on_1k.items():
        if len(files_list) < 2:
            continue    # this hash of fist 1k file bytes is unique, no need to spend CPU cycles on it

        for filename in files_list:
            try: 
                full_hash = get_hash(filename, chunk_size, first_chunk_only=False)
                duplicate = hashes_full.get(full_hash)
                if duplicate:
                    logger.info(f'Duplicate: {os.path.basename(duplicate)} | {os.path.basename(filename)}')
                    duplicates[duplicate].add(filename)
                else:
                    hashes_full[full_hash] = filename
            except (OSError,):
                logger.warning(f'Error reading file: {os.path.join(dirpath, filename)}')
                continue
    return duplicates

def single_yes_or_no_question(question, default_no=True):
    choices = ' [y/N]: ' if default_no else ' [Y/n]: '
    default_answer = 'n' if default_no else 'y'
    reply = str(input(question + choices)).lower().strip() or default_answer
    if reply[0] == 'y':
        return True
    if reply[0] == 'n':
        return False
    else:
        return False if default_no else True


def find_keep_file(files):
    filename_files_dict = {os.path.splitext(os.path.basename(f))[0]: i for i, f in enumerate(files)}
    filenames = list(filename_files_dict.keys())
    filenames.sort()
    filenames.sort(key=len)
    keep_file_idx = filename_files_dict[filenames[0]]
    return files[keep_file_idx]


def main(path, chunk_size, recursive, force):
    duplicates = check_for_duplicates(path, chunk_size, recursive)
    logger.info(f'Number of duplicates found: {sum([len(files_set) for __, files_set in duplicates.items()])}')
    if not force:
        delete = single_yes_or_no_question('Delete duplicates?')
    
    if delete:    
        for key_file, files_set in duplicates.items():
            files_set.add(key_file)
            keep_file = find_keep_file(list(files_set))
            logger.info(f'Keeping: {os.path.basename(keep_file)}')
            files_set.remove(keep_file)
            for f in files_set:
                logger.info(f'Deleting: {os.path.basename(f)}')
                os.remove(f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        'WhatsApp duplicate file remover', 
        description='Remove duplicated media, preserving the file with the shortest filename or earliest date encoded in the filename.')
    parser.add_argument('path', type=str, help='Path to WhatsApp media folder')
    parser.add_argument('-c', '--chunk-size', default=1024, type=int, help='Chunk size for heuristic, smaller values are generally faster but if many files have identical starting chunks, performance degrades as more full hashes are computed')
    parser.add_argument('-f', '--force', action='store_true', help='Delete duplicates without prompting')
    parser.add_argument('-r', '--recursive', default=False, action='store_true', help='Recursively process media')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s %(levelname)s: %(message)s')
    logger = logging.getLogger('find-duplicates')
    
    main(args.path, args.chunk_size, args.recursive, force=args.force)

