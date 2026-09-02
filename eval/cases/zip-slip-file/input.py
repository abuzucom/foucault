import os
import tarfile


def restore_backup(archive_path, target_dir):
    """Restore a user-uploaded backup archive."""
    with tarfile.open(archive_path) as tar:
        for member in tar.getmembers():
            dest = os.path.join(target_dir, member.name)
            tar.extract(member, target_dir)
    return target_dir
