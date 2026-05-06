from pathlib import Path


INDEX_HTML = Path(__file__).resolve().parents[1] / "web" / "index.html"


def test_team_workspace_panel_and_actions_exist():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert 'id="teamWorkspacePanel"' in html
    assert 'id="teamWorkspaceActions"' in html
    assert 'id="teamWorkspacePanel" style="display:none;' in html
    assert 'id="teamWorkspaceActions" style="display:none;' in html
    assert 'id="btnCreateTeamWorkspace"' in html
    assert 'id="btnAddTeamMember"' in html
    assert 'id="btnLoadTeamFormatRules"' in html
    assert 'id="btnSaveTeamFormatRules"' in html
    assert 'id="btnRunTeamBatchQA"' in html
    assert 'id="teamMemberEmail"' in html
    assert 'id="teamWorkspaceStatus"' in html
    assert 'id="teamWorkspacePlan"' in html
    assert 'id="teamWorkspaceInvites"' in html
    assert 'id="teamWorkspaceProgress"' in html
    assert 'id="teamWorkspaceMembers"' in html
    assert 'id="teamBatchQAResult"' in html
    assert 'id="teamBatchJobs"' in html
    assert 'id="teamActivityHistory"' in html
    assert 'id="teamBatchQADetails"' in html


def test_team_workspace_frontend_wires_new_api_actions():
    html = INDEX_HTML.read_text(encoding="utf-8")

    assert "function _setTeamWorkspaceVisibility(tier)" in html
    assert "function _setTeamWorkspaceVisibilityState(visible)" in html
    assert "async function _refreshTeamWorkspaceAccess(planTier)" in html
    assert "function _setTeamWorkspaceProgress(message, busy=false, isError=false)" in html
    assert "function _renderTeamWorkspacePlan(plan)" in html
    assert "function _formatPlanQuota(used, limit)" in html
    assert "function _renderTeamInvitations(invitations)" in html
    assert "function _renderTeamMembers(teamId, members)" in html
    assert "function _renderTeamActivityHistory(activities)" in html
    assert "function _renderTeamBatchJobs(jobs)" in html
    assert "function _getTeamInviteMessage(teamId, inviteEmail, role='member')" in html
    assert "async function copyTeamInviteMessage(teamId, inviteEmail, role='member')" in html
    assert "function openTeamInviteDraft(teamId, inviteEmail, role='member')" in html
    assert "async function sendTeamInviteEmail(teamId, inviteEmail, role='member')" in html
    assert "async function resendTeamInvite(teamId, inviteEmail, role='member')" in html
    assert "function _renderTeamWorkspaceStatus(data)" in html
    assert "function _renderTeamBatchQADetails(data)" in html
    assert "normalized==='team'||normalized==='enterprise'" in html
    assert "await _refreshTeamWorkspaceAccess(plan.tier);" in html
    assert "await _refreshTeamWorkspaceAccess('free');" in html
    assert "async addTeamMemberByEmail(email, role='member')" in html
    assert "async acceptTeamInvite(team_id)" in html
    assert "async cancelTeamInvite(team_id, email)" in html
    assert "async sendTeamInviteEmail(team_id, email, role='member')" in html
    assert "async startTeamBatchQA(files, categories)" in html
    assert "async getTeamBatchJobs()" in html
    assert "async function loadTeamWorkspace(force=false)" in html
    assert "if(panel.style.display==='none' && !force)return;" in html
    assert "_setTeamWorkspaceProgress(`正在批量检查 ${files.length} 份文档...`,true);" in html
    assert "const resp=await window.WC_API.getUsageAndPlan();" in html
    assert "async function createTeamWorkspace()" in html
    assert "async function addTeamMemberByEmail()" in html
    assert "async function acceptTeamInvite(teamId)" in html
    assert "async function refreshTeamBatchJobs()" in html
    assert "async function pollTeamBatchJob(jobId)" in html
    assert "copyTeamInviteMessage('" in html
    assert "openTeamInviteDraft('" in html
    assert "sendTeamInviteEmail('" in html
    assert "resendTeamInvite('" in html
    assert "cancelTeamInvite('" in html
    assert "navigator.clipboard?.writeText" in html
    assert "window.location.href=`mailto:" in html
    assert "async function loadTeamFormatRequirements()" in html
    assert "async function runTeamBatchQA()" in html
    assert "const started=await window.WC_API.startTeamBatchQA(files, ['typo','consistency','logic','format','crossref']);" in html
    assert "loadTeamWorkspace();" in html
