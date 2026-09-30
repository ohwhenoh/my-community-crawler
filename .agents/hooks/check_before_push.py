#!/usr/bin/env python3
import sys
import json
import subprocess
import glob
import os

def check_syntax(workspace_dir):
    """Check syntax of all python files in the workspace. Returns (bool, str)"""
    py_files = glob.glob(os.path.join(workspace_dir, "**/*.py"), recursive=True)
    for f in py_files:
        if "venv" in f: continue
        # py_compile does not check the execution but ensures there's no SyntaxError
        result = subprocess.run(["python3", "-m", "py_compile", f], capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"Syntax error in {os.path.basename(f)}:\n{result.stderr}"
    return True, ""


def check_dockerfile(workspace_dir):
    """Check if all root python files are copied in the Dockerfile if it exists."""
    dockerfile_path = os.path.join(workspace_dir, "Dockerfile")
    if not os.path.exists(dockerfile_path):
        return True, ""
        
    with open(dockerfile_path, 'r', encoding='utf-8') as f:
        dockerfile_content = f.read()
        
    # If Dockerfile copies all python files, we are safe
    if "COPY *.py" in dockerfile_content:
        return True, ""
        
    # Otherwise check if every .py file in root is explicitly copied
    root_py_files = glob.glob(os.path.join(workspace_dir, "*.py"))
    for f in root_py_files:
        basename = os.path.basename(f)
        if basename.startswith('test_') or basename.startswith('patch_') or basename.startswith('fix_'):
            continue
        if f"COPY {basename}" not in dockerfile_content:
            return False, f"Missing 'COPY {basename} .' in Dockerfile"
            
    return True, ""

def main():
    try:
        payload = json.loads(sys.stdin.read())
        tool_call = payload.get('toolCall', {})
        args = tool_call.get('args', {})
        cmd = args.get('CommandLine', '')
        
        # Get workspace paths
        workspaces = payload.get('workspacePaths', [])
        current_workspace = workspaces[0] if workspaces else None

        # Prevent git commit or git push if there are syntax errors
        if cmd and ("git commit" in cmd or "git push" in cmd):
            if current_workspace:
                is_valid, error_msg = check_syntax(current_workspace)
                if not is_valid:
                    print(json.dumps({
                        "decision": "deny",
                        "reason": f"❌ [Guardrail Block] 파이썬 문법 오류가 감지되어 커밋/푸시가 차단되었습니다.\n반드시 샌드박스에서 오류를 수정하고 (python3 -m py_compile) E2E 테스트를 거치세요.\n{error_msg}"
                    }))
                    return
                
                # Check Dockerfile consistency
                docker_valid, docker_error = check_dockerfile(current_workspace)
                if not docker_valid:
                    print(json.dumps({
                        "decision": "deny",
                        "reason": f"❌ [Guardrail Block] 도커파일(Dockerfile) 누락 감지!\n{docker_error}\n새로 생성한 파이썬 파일을 Dockerfile의 COPY 명령어에 추가하거나 'COPY *.py .' 로 변경하세요."
                    }))
                    return
        
        print(json.dumps({"decision": "allow"}))
        
    except Exception as e:
        print(json.dumps({"decision": "allow", "reason": f"Hook error: {e}"}))

if __name__ == "__main__":
    main()
