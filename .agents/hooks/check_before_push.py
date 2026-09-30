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
        
        print(json.dumps({"decision": "allow"}))
        
    except Exception as e:
        print(json.dumps({"decision": "allow", "reason": f"Hook error: {e}"}))

if __name__ == "__main__":
    main()
