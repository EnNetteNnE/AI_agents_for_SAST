import subprocess
import tempfile
import logging
from pathlib import Path
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class CodeQLValidator:
    # проверка CodeQL синтаксиса через реальную компиляцию C++ БД

    def __init__(self, codeql_path: str = "codeql", pack_dir: str = "codeql_pack", db_path: str = "cpp_test_db"):
        self.codeql_path = codeql_path
        self.pack_dir = Path(pack_dir).resolve()
        self.db_path = Path(db_path).resolve()
        self._verify_installed()
        self._verify_pack()
        self._verify_database()

    def _verify_installed(self):
        # проверить установлен ли CodeQL
        result = subprocess.run(
            [self.codeql_path, "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version_line = result.stdout.strip().split("\n")[0]
            logger.info(f"OK CodeQL найден: {version_line}")
        else:
            raise RuntimeError(f"CodeQL error: {result.stderr}")

    def _verify_pack(self):
        # проверить qlpack.yml
        qlpack = self.pack_dir / "qlpack.yml"
        if not qlpack.exists():
            raise RuntimeError(
                f"qlpack.yml not found in {self.pack_dir}. "
                "Создай с dependency на codeql/cpp-all."
            )

    def _verify_database(self):
        # проверить C++ database
        if not self.db_path.exists():
            raise RuntimeError(
                f"C++ database not found at {self.db_path}. "
                "cd minimal_cpp && codeql database create ../cpp_test_db --language=cpp --command='g++ -c test.cpp'"
            )
        logger.info(f"OK C++ БД найдена: {self.db_path}")

    def validate_syntax(self, rule: str) -> Tuple[bool, Optional[str]]:
        # возвращает True ТОЛЬКО если codeql query compile завершился с кодом 0
        quick_ok, quick_err = self._quick_syntax_check(rule)
        if not quick_ok:
            return False, quick_err

        rule_file = self.pack_dir / "tmp_rule.ql"
        rule_file.write_text(rule)

        cmd = [
            self.codeql_path,
            "query",
            "compile",
            "--dbscheme=../cpp_test_db/db-cpp/semmlecode.cpp.dbscheme", 
            str(rule_file),
        ]
        logger.info("Running: %s (cwd=%s)", " ".join(cmd), self.pack_dir)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=40,  # хватит
                cwd=self.pack_dir,
            )
        except subprocess.TimeoutExpired:
            return False, "CodeQL compilation timeout (>40s)"
        finally:
            if rule_file.exists():
                rule_file.unlink()

        if result.returncode == 0:
            logger.info("OK Компиляция прошла успешно в реальной C++ БД")
            return True, None

        error_msg = result.stderr or result.stdout
        logger.warning("ERROR Компиляция неуспешна: %s", error_msg[:400])
        return False, self._extract_error(error_msg)

    def _quick_syntax_check(self, code: str) -> Tuple[bool, Optional[str]]:
        # быстрая проверка перед компиляцией
        if not code or len(code.strip()) < 50:
            return False, "Code too short (<50 chars)"
        if "import" not in code:
            return False, "Missing 'import' statement"
        if "select" not in code and "from" not in code:
            return False, "Missing 'select' or 'from' clause"
        brackets = {"(": ")", "{": "}", "[": "]"}
        for open_br, close_br in brackets.items():
            if code.count(open_br) != code.count(close_br):
                return False, f"Mismatched {open_br}/{close_br}"
        if code.count('"') % 2 != 0:
            return False, "Unclosed string literal"
        return True, None

    def _extract_error(self, error_msg: str) -> str:
        # извлечь части ошибки
        lines = error_msg.split("\n")
        error_lines = [l for l in lines if "error" in l.lower() or "failed" in l.lower()]
        if error_lines:
            return "\n".join(error_lines[:2])
        return error_msg[:500]

    def extract_error_snippet(self, error_msg: str) -> str:
        # для LLM
        return self._extract_error(error_msg)
