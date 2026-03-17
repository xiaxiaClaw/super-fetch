#!/usr/bin/env python3
"""
反查网页链接工具 (SQLite 高并发安全版)
支持：批量反查、全局清理、指定命名空间清理
"""

import sqlite3
import sys
import os
import argparse

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "links.db")

def main():
    parser = argparse.ArgumentParser(description="根据代号反查原始链接工具")
    parser.add_argument("ids", nargs="*", help="链接代号(如 k9-1) 或 命名空间(如 k9)")
    parser.add_argument("--clear", "-c", action="store_true", help="清理模式。若带参数则清理指定命名空间，不带参数则清空全部。")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH) and not args.clear:
        print("错误: 未找到链接数据库 links.db")
        sys.exit(1)
        
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            # 1. 处理清理指令
            if args.clear:
                if not args.ids:
                    # 全局清理
                    conn.execute("DELETE FROM links")
                    print("[*] 🧹 已清空数据库中所有链接记录。")
                else:
                    # 指定命名空间清理 (例如清理 k9-*)
                    for ns in args.ids:
                        clean_ns = ns.lstrip("@").split("-")[0] # 兼容输入 k9 或 k9-1
                        cursor = conn.execute("DELETE FROM links WHERE id LIKE ?", (f"{clean_ns}-%",))
                        print(f"[*] 🧹 已清理命名空间: {clean_ns} (影响 {cursor.rowcount} 条记录)")
                
                conn.execute("VACUUM") 
                return

            # 2. 处理查询指令
            if args.ids:
                cursor = conn.cursor()
                for lid in args.ids:
                    clean_id = lid.lstrip("@")
                    cursor.execute("SELECT url FROM links WHERE id = ?", (clean_id,))
                    row = cursor.fetchone()
                    if row:
                        print(f"@{clean_id} -> {row[0]}")
                    else:
                        print(f"@{clean_id} -> [未找到或已清理]")
                    
    except Exception as e:
        print(f"数据库操作失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()