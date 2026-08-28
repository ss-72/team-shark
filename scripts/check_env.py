"""CI 向け環境変数チェックスクリプト

チェック項目:
 - SECRET_KEY
 - (DATABASE_URL) または (MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE)
 - ADMIN_USERNAME
 - ADMIN_PASSWORD

使い方: CI ジョブでこのスクリプトを実行し、非ゼロ終了でジョブを失敗させてください。
"""
import os
import sys


def check_db_env():
    if os.getenv('DATABASE_URL'):
        return True
    mysql_keys = ('MYSQL_HOST', 'MYSQL_USER', 'MYSQL_PASSWORD', 'MYSQL_DATABASE')
    return all(os.getenv(k) for k in mysql_keys)


def main():
    missing = []

    if not os.getenv('SECRET_KEY'):
        missing.append('SECRET_KEY')

    if not check_db_env():
        missing.append('DATABASE_URL or MYSQL_HOST/MYSQL_USER/MYSQL_PASSWORD/MYSQL_DATABASE')

    if not os.getenv('ADMIN_USERNAME'):
        missing.append('ADMIN_USERNAME')
    if not os.getenv('ADMIN_PASSWORD'):
        missing.append('ADMIN_PASSWORD')

    if missing:
        print('ERROR: Missing required environment variables:')
        for m in missing:
            print(f' - {m}')
        print('\nPlease set the missing variables in your CI environment or secrets store.')
        sys.exit(2)

    # Minimal positive output for CI logs; do not print secrets
    print('Environment check passed: required secrets and DB config present.')
    sys.exit(0)


if __name__ == '__main__':
    main()
