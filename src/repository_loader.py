import os
import subprocess
from pathlib import Path
from typing import List, Tuple
from .models import RepositoryContext, Document


class RepositoryLoader:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def clone_repo(self, repo_url: str) -> RepositoryContext:
        if os.path.isdir(repo_url):
            repo_name = os.path.basename(repo_url)
            local_path = Path(repo_url)
            print(f"使用本地仓库: {local_path}")
        else:
            repo_name = repo_url.split("/")[-1].replace(".git", "")
            local_path = self.data_dir / repo_name

            if local_path.exists():
                print(f"仓库已存在: {local_path}")
            else:
                print(f"正在克隆仓库: {repo_url}")
                subprocess.run(["git", "clone", repo_url, str(local_path)], check=True)

        return RepositoryContext(
            repo_url=repo_url,
            repo_name=repo_name,
            local_path=str(local_path)
        )

    def load_documents(self, context: RepositoryContext) -> List[Document]:
        documents = []
        repo_path = Path(context.local_path)

        md_files = list(repo_path.rglob("*.md"))
        print(f"找到 {len(md_files)} 个 Markdown 文件")

        for md_file in md_files:
            relative_path = md_file.relative_to(repo_path)
            if self._should_ignore(str(relative_path)):
                continue

            try:
                content = self._read_file_with_fallback(md_file)
                title = self._extract_title(content, str(relative_path))
                headings = self._extract_headings(content)

                documents.append(Document(
                    path=str(relative_path),
                    title=title,
                    content=content,
                    headings=headings
                ))
            except Exception as e:
                print(f"读取文件失败 {relative_path}: {e}")

        context.documents = documents
        return documents

    def load_code_files(self, context: RepositoryContext) -> List[Tuple[str, str]]:
        code_files = []
        repo_path = Path(context.local_path)

        extensions = ["*.py", "*.js", "*.ts", "*.java", "*.go", "*.rs"]

        for ext in extensions:
            files = list(repo_path.rglob(ext))
            for file_path in files:
                relative_path = str(file_path.relative_to(repo_path))
                if self._should_ignore(relative_path):
                    continue

                try:
                    content = self._read_file_with_fallback(file_path)
                    code_files.append((relative_path, content))
                except Exception as e:
                    print(f"读取代码文件失败 {relative_path}: {e}")

        print(f"找到 {len(code_files)} 个代码文件")
        return code_files

    def _read_file_with_fallback(self, file_path: Path) -> str:
        encodings = ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1", "gbk"]
        for encoding in encodings:
            try:
                return file_path.read_text(encoding=encoding)
            except (UnicodeDecodeError, UnicodeError):
                continue
        raise ValueError(f"Unable to read file with any encoding: {file_path}")

    def _should_ignore(self, path: str) -> bool:
        ignore_patterns = ["node_modules", "dist", "build", ".git", "__pycache__", ".venv", "venv", "env"]
        return any(pattern in path for pattern in ignore_patterns)

    def _extract_title(self, content: str, path: str) -> str:
        for line in content.split("\n"):
            if line.startswith("# "):
                return line[2:].strip()
        return Path(path).stem

    def _extract_headings(self, content: str) -> List[str]:
        headings = []
        for line in content.split("\n"):
            if line.startswith("#"):
                headings.append(line.strip())
        return headings