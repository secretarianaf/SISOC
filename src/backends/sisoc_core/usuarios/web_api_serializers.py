"""Explicit output whitelist and schema for the web session context."""

# Output-only DTOs, following api_inet_serializers; persistence is not supported.
# pylint: disable=abstract-method
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers


class WebSessionErrorSerializer(serializers.Serializer):
    detail = serializers.CharField()


class WebUserSerializer(serializers.Serializer):
    username = serializers.CharField()
    display_name = serializers.CharField()
    avatar_initial = serializers.CharField(allow_blank=True)
    role_label = serializers.CharField()


class WebAccessSerializer(serializers.Serializer):
    state = serializers.ChoiceField(
        choices=[
            "ready",
            "web_access_denied",
            "password_change_required",
            "profile_confirmation_required",
            "mandatory_survey_required",
        ]
    )
    required_action_url = serializers.CharField(allow_null=True)


class WebNavigationNodeSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    href = serializers.CharField(allow_null=True)
    children = serializers.SerializerMethodField()

    @extend_schema_field(
        {"type": "array", "items": {"$ref": "#/components/schemas/WebNavigationNode"}}
    )
    def get_children(self, obj):
        return WebNavigationNodeSerializer(obj["children"], many=True).data


class InsumosCapabilitiesSerializer(serializers.Serializer):
    can_view = serializers.BooleanField()
    show_management = serializers.BooleanField()
    show_categories = serializers.BooleanField()


class WebCapabilitiesSerializer(serializers.Serializer):
    insumos = InsumosCapabilitiesSerializer()


class WebSessionContextSerializer(serializers.Serializer):
    user = WebUserSerializer(allow_null=True)
    access = WebAccessSerializer()
    navigation = WebNavigationNodeSerializer(many=True)
    capabilities = WebCapabilitiesSerializer()
    footer_version_label = serializers.CharField()
