import os

# --- Настройки ---
# Папки и файлы, которые нужно исключить из сборки
EXCLUDE_DIRS = {'.git', '.idea', '.vscode', '__pycache__', '.venv', 'venv'}
EXCLUDE_FILES = {'.gitignore', 'project_archive.zip', 'bundle_for_ai.py'}
# Имя выходного файла
OUTPUT_FILE = 'project_bundle.txt'
# --- Конец настроек ---

def bundle_project(project_path='.'):
    """Собирает все текстовые файлы проекта в один .txt файл."""
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        f_out.write(f"# BUNDLE OF PROJECT: {os.path.abspath(project_path)}\n\n")
        for root, dirs, files in os.walk(project_path):
            # Исключаем ненужные директории
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                if file in EXCLUDE_FILES:
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, project_path)

                try:
                    with open(file_path, 'r', encoding='utf-8') as f_in:
                        content = f_in.read()
                    
                    f_out.write("-" * 80 + "\n")
                    f_out.write(f"--- FILE: {relative_path.replace(os.sep, '/')}\n")
                    f_out.write("-" * 80 + "\n")
                    f_out.write(content)
                    f_out.write("\n\n")
                    print(f"[+] Added: {relative_path}")

                except Exception as e:
                    # Пропускаем бинарные файлы или файлы с проблемами кодировки
                    f_out.write("-" * 80 + "\n")
                    f_out.write(f"--- SKIPPED (binary or error): {relative_path.replace(os.sep, '/')} | Reason: {e}\n")
                    f_out.write("-" * 80 + "\n\n")
                    print(f"[-] Skipped: {relative_path} ({e})")

    print(f"\nProject bundled into: {OUTPUT_FILE}")

if __name__ == '__main__':
    bundle_project()