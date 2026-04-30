from pathlib import Path


INDEX_HTML = Path(__file__).resolve().parents[1] / "web" / "index.html"


def test_team_workspace_panel_and_actions_exist():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="teamWorkspacePanel"' in html
    assert 'id="teamWorkspaceActions"' in html
    assert 'id="btnCreateTeamWorkspace"' in html
    assert 'id="btnAddTeamMember"' in html
    assert 'id="btnLoadTeamFormatRules"' in html
    assert 'id="btnSaveTeamFormatRules"' in html
    assert 'id="btnRunTeamBatchQA"' in html
    assert 'id="teamMemberEmail"' in html
    assert 'id="teamWorkspaceMembers"' in html
    assert 'id="teamBatchQAResult"' in html


def test_team_workspace_frontend_wires_new_api_actions():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "async addTeamMemberByEmail(email, role='member')" in html
    assert "async function loadTeamWorkspace()" in html
    assert "async function createTeamWorkspace()" in html
    assert "async function addTeamMemberByEmail()" in html
    assert "async function loadTeamFormatRequirements()" in html
    assert "async function runTeamBatchQA()" in html
    assert "loadTeamWorkspace();" in html
