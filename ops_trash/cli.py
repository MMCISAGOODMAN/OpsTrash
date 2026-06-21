#!/usr/bin/env python3
import argparse
import sys
import os
import glob
from .storage import add_file_to_trash, find_entries, get_size_and_count, clean_older_than, get_last_entry, restore_entry, get_stats, read_metadata, write_metadata, ensure_dirs, METADATA_FILE, CONFIG_FILE
from .utils import human_size
from .colors import green, red, yellow


def cmd_trash_put(args):
    paths = []
    for p in args.paths:
        # expand globs
        matches = glob.glob(p)
        if matches:
            paths.extend(matches)
        else:
            paths.append(p)
    for p in paths:
        if args.bypass:
            # direct delete
            if os.path.isdir(p):
                import shutil
                shutil.rmtree(p)
                print(f"Deleted directory: {p}")
            else:
                try:
                    os.remove(p)
                    print(f"Deleted: {p}")
                except Exception as e:
                    print(f"Error deleting {p}: {e}")
            continue
        try:
            entry = add_file_to_trash(p)
            print(green(f"✓ 已移入回收站: {os.path.basename(entry['original_path'])} (ID: {entry['id']})"))
        except Exception as e:
            print(red(f"Error: {e}"))


def cmd_list(args):
    meta = read_metadata()
    files = sorted(meta.get('files', []), key=lambda x: x.get('deleted_at', ''), reverse=True)
    if args.limit:
        files = files[:args.limit]
    print(f"ID  原路径\t删除时间\t大小\t用户")
    for f in files:
        print(f"{f['id']}\t{f['original_path']}\t{f['deleted_at']}\t{human_size(f.get('size',0))}\t{f.get('user')}")


def cmd_last(args):
    last = get_last_entry()
    if not last:
        print(yellow("回收站空"))
        return
    # attempt restore with prompt
    print(f"Last deleted: ID={last['id']} {last['original_path']}")
    dest = last['original_path']
    if os.path.exists(dest):
        ans = input(f"目标已存在: {dest}\n是否覆盖? (y/N): ")
        if ans.lower() != 'y':
            print(yellow("跳过恢复"))
            return
        restored = restore_entry(last['id'], overwrite=True)
    else:
        restored = restore_entry(last['id'])
    print(green(f"✓ 已恢复: {restored}"))


def cmd_restore(args):
    ids = [int(i) for i in args.ids]
    for id_ in ids:
        try:
            # check original path
            meta = read_metadata()
            entry = next((e for e in meta.get('files', []) if e['id']==id_), None)
            if not entry:
                print(yellow(f"ID {id_} 未找到"))
                continue
            dest = entry['original_path']
            if os.path.exists(dest):
                ans = input(f"目标已存在: {dest}\n是否覆盖? (y/N): ")
                if ans.lower() != 'y':
                    print(yellow("跳过"))
                    continue
                restored = restore_entry(id_, overwrite=True)
            else:
                restored = restore_entry(id_)
            print(green(f"✓ 已恢复: {restored}"))
        except Exception as e:
            print(red(f"Error restoring {id_}: {e}"))


def cmd_clean(args):
    days = int(args.days) if args.days is not None else 7
    removed, freed = clean_older_than(days)
    print(green(f"✓ 已清理 {removed} 个过期文件（已存在{days}天以上）"))
    print(green(f"释放空间: {human_size(freed)}"))


def cmd_search(args):
    res = find_entries(args.query)
    for e in res:
        # highlight match
        print(f"{e['id']}\t{e['original_path']}\t{e['deleted_at']}\t{human_size(e.get('size',0))}")


def cmd_size(args):
    count, total = get_size_and_count()
    print(f"文件数: {count}  总大小: {human_size(total)}")


def cmd_stats(args):
    s = get_stats()
    print(f"总文件数: {s['total_files']}")
    print(f"总大小: {human_size(s['total_size'])}")
    print(f"今日删除数: {s['today_count']}")
    print(f"平均每日删除量: {s['avg_daily']:.2f}")
    print(f"最老文件时间: {s['oldest']}")
    print(f"过期文件数量: {s['expired']}")


def cmd_web(args):
    from .web import run_web
    host = args.host or None
    port = args.port or None
    run_web(host=args.host, port=args.port, daemon=args.daemon)


def cmd_config(args):
    if args.action == 'show':
        import json
        if os.path.exists(CONFIG_FILE):
            print(json.dumps(json.load(open(CONFIG_FILE)), indent=2, ensure_ascii=False))
        else:
            print('no config')
    elif args.action == 'set':
        import json
        if not os.path.exists(CONFIG_FILE):
            print('no config file')
            return
        cfg = json.load(open(CONFIG_FILE))
        cfg[args.key] = _parse_value(args.value)
        json.dump(cfg, open(CONFIG_FILE, 'w'), indent=2, ensure_ascii=False)
        print('配置已更新')


def _parse_value(v):
    # try int, float, bool
    if v.lower() in ('true','false'):
        return v.lower()=='true'
    try:
        if '.' in v:
            return float(v)
        return int(v)
    except Exception:
        return v


def main(argv=None):
    ensure_dirs()
    parser = argparse.ArgumentParser(prog='undo', description='Ops Trash CLI')
    sub = parser.add_subparsers(dest='cmd')

    p_trash = sub.add_parser('trash-put')
    p_trash.add_argument('paths', nargs='+')
    p_trash.add_argument('--bypass', action='store_true', help='Bypass trash and delete directly')
    p_trash.set_defaults(func=cmd_trash_put)

    p_list = sub.add_parser('list')
    p_list.add_argument('--limit', type=int)
    p_list.set_defaults(func=cmd_list)

    p_last = sub.add_parser('last')
    p_last.set_defaults(func=cmd_last)

    p_restore = sub.add_parser('restore')
    p_restore.add_argument('ids', nargs='+')
    p_restore.set_defaults(func=cmd_restore)

    p_clean = sub.add_parser('clean')
    p_clean.add_argument('days', nargs='?', default=None)
    p_clean.set_defaults(func=cmd_clean)

    p_search = sub.add_parser('search')
    p_search.add_argument('query')
    p_search.set_defaults(func=cmd_search)

    p_size = sub.add_parser('size')
    p_size.set_defaults(func=cmd_size)

    p_stats = sub.add_parser('stats')
    p_stats.set_defaults(func=cmd_stats)

    p_web = sub.add_parser('web')
    p_web.add_argument('--port', type=int, default=8080)
    p_web.add_argument('--host', default='0.0.0.0')
    p_web.add_argument('--daemon', action='store_true')
    p_web.set_defaults(func=cmd_web)

    p_cfg = sub.add_parser('config')
    p_cfg.add_argument('action', choices=['show','set'])
    p_cfg.add_argument('key', nargs='?')
    p_cfg.add_argument('value', nargs='?')
    p_cfg.set_defaults(func=cmd_config)

    # compatibility: allow calling as `trash-put` directly
    args = parser.parse_args(argv)
    if args.cmd is None:
        parser.print_help()
        return 1
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())

