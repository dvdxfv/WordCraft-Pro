import tempfile
from pathlib import Path

from core.supabase_client import SupabaseClient


class _FakeBucket:
    def __init__(self):
        self.upload_calls = []

    def upload(self, storage_path, file_content, options):
        self.upload_calls.append((storage_path, file_content, options))
        return {"path": storage_path}

    def get_public_url(self, storage_path):
        return f"https://example.com/storage/v1/object/public/templates/{storage_path}"


class _FakeStorage:
    def __init__(self, bucket):
        self.bucket = bucket

    def from_(self, bucket_name):
        assert bucket_name == "templates"
        return self.bucket


class _FakeClient:
    def __init__(self, bucket):
        self.storage = _FakeStorage(bucket)


def test_build_template_storage_path_keeps_extension_and_generates_unique_name():
    path1 = SupabaseClient._build_template_storage_path("user-1", r"C:\tmp\sample.docx", "模板")
    path2 = SupabaseClient._build_template_storage_path("user-1", r"C:\tmp\sample.docx", "模板")

    assert path1.startswith("user-1/")
    assert path2.startswith("user-1/")
    assert path1.endswith(".docx")
    assert path2.endswith(".docx")
    assert path1 != path2


def test_upload_template_file_uses_unique_storage_path_and_detected_mime():
    temp_dir = Path(tempfile.mkdtemp(dir=r"C:\tmp"))
    template_file = temp_dir / "reference.docx"
    template_file.write_bytes(b"test-template")

    bucket = _FakeBucket()
    client = SupabaseClient.__new__(SupabaseClient)
    client.client = _FakeClient(bucket)

    try:
        public_url = client.upload_template_file("user-1", str(template_file), "测试模板")

        assert public_url.startswith("https://example.com/storage/v1/object/public/templates/user-1/")
        assert bucket.upload_calls
        storage_path, file_content, options = bucket.upload_calls[0]
        assert storage_path.startswith("user-1/")
        assert storage_path.endswith(".docx")
        assert file_content == b"test-template"
        assert options["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    finally:
        if template_file.exists():
            template_file.unlink()
        temp_dir.rmdir()
