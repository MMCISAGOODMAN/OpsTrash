import os
import json
import fcntl
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from .utils import now_str, timestamp_str, short_rand8, current_user

HOME = Path.home()
TRASH_DIR = HOME / '.ops_trash'
FILES_DIR = TRASH_DIR / 'files'
METADATA_FILE = TRASH_DIR / 'metadata.json'
CONFIG_FILE = TRASH_DIR / 'config.json'
LOG_FILE = TRASH_DIR / 'operations.log'


def ensure_dirs():
    FILES_DIR.mkdir(parents=True, exist_ok=True)
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    if not METADATA_FILE.exists():
        atomic_write_json({'files': [], 'counter': 0}, METADATA_FILE)
    if not CONFIG_FILE.exists():
        atomic_write_json({'max_retention_days': 7, 'max_size_gb': 10, 'web_port': 8080, 'web_host': '0.0.0.0', 'auto_clean': True, 'log_enabled': True}, CONFIG_FILE)
    if not LOG_FILE.exists():
        LOG_FILE.touch()


def _lock_file(fp):
    fcntl.flock(fp.fileno(), fcntl.LOCK_EX)


def _unlock_file(fp):
    try:
        fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
    except Exception:
        pass


def atomic_write_json(obj, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile('w', delete=False, dir=str(path.parent)) as tf:
        json.dump(obj, tf, indent=2, ensure_ascii=False)
        tf.flush()
        os.fsync(tf.fileno())
        tmpname = tf.name
    os.replace(tmpname, str(path))


def read_metadata():
    ensure_dirs()
    with open(METADATA_FILE, 'r') as f:
        # no locking for read-only; could lock for safety
        return json.load(f)


def write_metadata(metadata):
    ensure_dirs()
    # lock the metadata file while writing
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, 'r+') as f:
        _lock_file(f)
        try:
            # write to temp and replace
            atomic_write_json(metadata, METADATA_FILE)
        finally:
            _unlock_file(f)


def log_operation(msg: str):
    ensure_dirs()
    timestamp = now_str()
    with open(LOG_FILE, 'a+') as f:
        _lock_file(f)
        try:
            f.write(f"[{timestamp}] {msg}\n")
            f.flush()
            os.fsync(f.fileno())
        finally:
            _unlock_file(f)


def add_file_to_trash(src_path: str):
    ensure_dirs()
    p = Path(src_path)
    if not p.exists():
        raise FileNotFoundError(str(src_path))

    meta = read_metadata()
    counter = meta.get('counter', 0) + 1
    meta['counter'] = counter

    base = p.name
    tstamp = timestamp_str()
    rand = short_rand8()
    trash_name = f"{tstamp}_{base}_{rand}"
    dest = FILES_DIR / trash_name

    # move file into files dir (preserve metadata)
    shutil.move(str(p), str(dest))

    size = dest.stat().st_size
    entry = {
        'id': counter,
        'original_path': str(p.resolve()),
        'trash_name': trash_name,
        'deleted_at': now_str(),
        'user': current_user(),
        'size': size
    }
    meta.setdefault('files', [])
    meta['files'].append(entry)
    write_metadata(meta)
    log_operation(f"TRASH PUT id={counter} original={entry['original_path']} trash={trash_name} size={size}")
    return entry


def restore_entry(entry_id: int, overwrite=False, rename_on_conflict=False):
    ensure_dirs()
    meta = read_metadata()
    files = meta.get('files', [])
    for i, e in enumerate(files):
        if e['id'] == entry_id:
            src = FILES_DIR / e['trash_name']
            dest = Path(e['original_path'])
            if dest.exists():
                if overwrite:
                    if dest.is_dir():
                        shutil.rmtree(str(dest))
                    else:
                        dest.unlink()
                elif rename_on_conflict:
                    dest = dest.with_name(dest.name + f".restored.{e['id']}")
                else:
                    raise FileExistsError(str(dest))
            # ensure parent dir exists
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dest))
            try:
                shutil.copystat(str(dest), str(dest))
            except Exception:
                pass
            # remove metadata entry
            del files[i]
            meta['files'] = files
            write_metadata(meta)
            log_operation(f"RESTORE id={entry_id} to={dest}")
            return str(dest)
    raise KeyError(f"Entry id={entry_id} not found")


def clean_older_than(days: int):
    ensure_dirs()
    meta = read_metadata()
    files = meta.get('files', [])
    import datetime
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    removed = 0
    freed = 0
    new_files = []
    for e in files:
        try:
            dt = datetime.datetime.strptime(e['deleted_at'], '%Y-%m-%d %H:%M:%S')
        except Exception:
            new_files.append(e)
            continue
        if dt < cutoff:
            trash_path = FILES_DIR / e['trash_name']
            if trash_path.exists():
                try:
                    if trash_path.is_dir():
                        shutil.rmtree(str(trash_path))
                    else:
                        size = trash_path.stat().st_size
                        freed += size
                        trash_path.unlink()
                except Exception:
                    pass
            removed += 1
            log_operation(f"CLEAN removed id={e['id']} trash={e['trash_name']}")
        else:
            new_files.append(e)
    meta['files'] = new_files
    write_metadata(meta)
    return removed, freed


def get_size_and_count():
    ensure_dirs()
    meta = read_metadata()
    files = meta.get('files', [])
    total = sum(f.get('size', 0) for f in files)
    return len(files), total


def find_entries(query: str):
    ensure_dirs()
    meta = read_metadata()
    q = query.lower()
    res = [e for e in meta.get('files', []) if q in e['trash_name'].lower() or q in e['original_path'].lower()]
    return res


def get_last_entry():
    ensure_dirs()
    meta = read_metadata()
    files = meta.get('files', [])
    if not files:
        return None
    # sort by deleted_at desc
    files_sorted = sorted(files, key=lambda x: x.get('deleted_at', ''), reverse=True)
    return files_sorted[0]


def get_stats():
    ensure_dirs()
    import datetime
    meta = read_metadata()
    files = meta.get('files', [])
    total_files = len(files)
    total_size = sum(f.get('size', 0) for f in files)
    today = datetime.datetime.now().date()
    today_count = 0
    dates = {}
    oldest = None
    for f in files:
        try:
            dt = datetime.datetime.strptime(f['deleted_at'], '%Y-%m-%d %H:%M:%S')
        except Exception:
            continue
        d = dt.date()
        dates.setdefault(d, 0)
        dates[d] += 1
        if d == today:
            today_count += 1
        if oldest is None or dt < oldest:
            oldest = dt
    avg_daily = sum(dates.values()) / max(1, len(dates))
    # expired count
    cfg = json.load(open(CONFIG_FILE)) if CONFIG_FILE.exists() else {}
    retention = int(cfg.get('max_retention_days', 7))
    cutoff = datetime.datetime.now() - datetime.timedelta(days=retention)
    expired = sum(1 for f in files if datetime.datetime.strptime(f['deleted_at'], '%Y-%m-%d %H:%M:%S') < cutoff)
    return {
        'total_files': total_files,
        'total_size': total_size,
        'today_count': today_count,
        'avg_daily': avg_daily,
        'oldest': oldest.strftime('%Y-%m-%d %H:%M:%S') if oldest else None,
        'expired': expired,
        'current_user': current_user(),
    }

