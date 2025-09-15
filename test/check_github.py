import sys
sys.path.append(sys.path[0].split("test")[0])

from tool import github_tool as gt

issue = gt.get_issue_by_issue_id("plait-board/drawnix" , 297)
print(issue.title)