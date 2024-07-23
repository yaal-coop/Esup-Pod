from pod.activitypub.models import ExternalVideo
from pod.video.models import LANG_CHOICES

import logging

logger = logging.getLogger(__name__)


def ap_video_to_external_video(payload, source_instance):
    """Create an ExternalVideo object from an AP Video payload."""

    video_source_links = [
        {
            "type": link["mediaType"],
            "src": link["href"],
            "size": link["size"],
            "width": link["width"],
            "height": link["height"],
        }
        for link in payload["url"]
        if "mediaType" in link and link["mediaType"] == "video/mp4"
    ]
    if not video_source_links:
        tags = []
        for link in payload["url"]:
            if "tag" in link:
                tags.extend(link["tag"])
        video_source_links = [
            {
                "type": link["mediaType"],
                "src": link["href"],
                "size": link["size"],
                "width": link["width"],
                "height": link["height"],
            }
            for link in tags
            if "mediaType" in link and link["mediaType"] == "video/mp4"
        ]

    external_video_attributes = {
        "ap_id": payload["id"],
        "videos": video_source_links,
        "title": payload["name"],
        "date_added": payload["published"],
        "thumbnail": [icon for icon in payload["icon"] if "thumbnails" in icon["url"]][0][
            "url"
        ],
        "duration": int(payload["duration"].lstrip("PT").rstrip("S")),
        "viewcount": payload["views"],
        "source_instance": source_instance,
    }

    if (
        "language" in payload
        and "identifier" in payload["language"]
        and (identifier := payload["language"]["identifier"])
        and identifier in LANG_CHOICES
    ):
        external_video_attributes["main_lang"] = identifier

    if "content" in payload and (content := payload["content"]):
        external_video_attributes["description"] = content

    external_video, created = ExternalVideo.objects.update_or_create(
        ap_id=external_video_attributes["ap_id"],
        defaults=external_video_attributes,
    )

    if created:
        logger.info(
            "ActivityPub external video %s created from %s instance",
            external_video,
            source_instance,
        )
    else:
        logger.info(
            "ActivityPub external video %s updated from %s instance",
            external_video,
            source_instance,
        )

    return external_video
