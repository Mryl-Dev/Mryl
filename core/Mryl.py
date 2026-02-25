from Lexer import Lexer
from Parser import Parser
from TypeChecker import TypeChecker
from Interpreter import Interpreter, MrylRuntimeError
from CodeGenerator import CodeGenerator
import subprocess
import os
import sys

# Windows コンソールの cp932 エンコード問題を回避: stdout を UTF-8 に固定
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Get input file from command line argument, default to advanced_methods.ml
# input_file = sys.argv[1] if len(sys.argv) > 1 else "./tests/test_10_async_await.ml"
input_file = sys.argv[1] if len(sys.argv) > 1 else "./my/async.ml"

with open(input_file, "r", encoding="utf-8-sig") as f:
    source = f.read()

# Lexer
lexer = Lexer(source)
tokens = []
while True:
    tok = lexer.read_token()
    tokens.append(tok)
    if tok.kind.name == "EOF":
        break

# Parser
parser = Parser(tokens)
program = parser.parse_program()

# Check Types
checker = TypeChecker()
checker.check_program(program)

# Interpreter Execution
print("=== Python Interpreter ===")
interp = Interpreter()
interp.source_file = os.path.basename(input_file)  # e.g. "match_test.ml"
python_exit_code = 0
try:
    interp.run(program)
except MrylRuntimeError as e:
    # Brief message to stdout
    print(f"\n[FATAL] {e.format_brief()}")
    print("  See stderr for the full error report.\n")
    # Detailed report to stderr
    print(e.format_detail(), file=sys.stderr)
    python_exit_code = 1
    # C code generation is still performed so the compiled binary can reproduce the error
except Exception as e:
    # 例: asyncio event loop 問題など — Python 側だけの問題でも C コード生成を続行
    print(f"\n[WARNING] Python interpreter error: {e}")
    python_exit_code = 1

# C Code Generation
print("\n=== C Code Generation ===")
bin_dir = os.path.join(os.getcwd(), "bin")
os.makedirs(bin_dir, exist_ok=True)
c_out = os.path.join(bin_dir, "Mryl.c")
exe_out = os.path.join(bin_dir, "Mryl.exe")
gen = CodeGenerator()
c_code = gen.generate(program)
with open(c_out, "w") as f:
    f.write(c_code)
print(f"OK - C code generated: {c_out}")

# Compile C code using gcc (via Cygwin bash)
print("\n=== C Compilation ===")
try:
    # Cygwin bash path (adjust if needed)
    cygwin_bash = r"C:\cygwin64\bin\bash.exe"
    cwd = os.getcwd().replace('\\', '/')
    # Convert C: to /cygdrive/c for Cygwin
    if cwd[1:3] == ':\\':
        cwd = '/cygdrive/' + cwd[0].lower() + cwd[2:]
    cyg_c   = f"{cwd}/bin/Mryl.c"
    cyg_exe = f"{cwd}/bin/Mryl.exe"
    compile_cmd = f"gcc -o {cyg_exe} {cyg_c}"
    result = subprocess.run(
        [cygwin_bash, "-l", "-c", compile_cmd],
        capture_output=True,
        cwd=os.getcwd()
    )

    if result.returncode == 0:
        print(f"OK - Compilation successful: {exe_out}")
    else:
        stderr_text = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
        print("ERROR - Compilation failed:")
        print(stderr_text)
except Exception as e:
    print(f"ERROR - {e}")
    sys.exit(1)

# Run the compiled executable
print("\n=== Native Execution ===")
try:
    cygwin_bash = r"C:\cygwin64\bin\bash.exe"
    cwd = os.getcwd().replace('\\', '/')
    # Convert C: to /cygdrive/c for Cygwin
    if cwd[1:3] == ':\\':
        cwd = '/cygdrive/' + cwd[0].lower() + cwd[2:]
    exec_cmd = f"{cwd}/bin/Mryl.exe"
    exec_result = subprocess.run(
        [cygwin_bash, "-l", "-c", exec_cmd],
        capture_output=True,
        cwd=os.getcwd()
    )
    if exec_result.stdout:
        print(exec_result.stdout.decode('utf-8', errors='replace'), end="")
    print(f"Program returned: {exec_result.returncode}")

except Exception as e:
    print(f"ERROR - {e}")
