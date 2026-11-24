from django.views import View

from core.v2_frontend import frontend_v2


class InsumosPreviewEntryView(View):
    """Forward an authorized INS-A HTML entry to the existing V2 proxy."""

    http_method_names = ["get", "head"]
    asset_path = ""

    def get(self, request, asset_path=None):
        requested_path = self.asset_path if asset_path is None else asset_path
        return frontend_v2(request, module="sisoc", asset_path=requested_path)
