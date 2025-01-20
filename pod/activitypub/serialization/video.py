from django.template.defaultfilters import slugify
from django.urls import reverse
from markdownify import markdownify

from pod.activitypub.constants import AP_LICENSE_MAPPING
from pod.activitypub.models import ExternalVideo
from pod.activitypub.utils import ap_url, make_magnet_url, stable_uuid


def ap_video_to_external_video(payload):
    """Create an ExternalVideo object from an AP Video payload."""
    return ExternalVideo.objects.create()


def video_to_ap_video(video):
    return {
        "id": ap_url(reverse("activitypub:video", kwargs={"slug": video.slug})),
        "to": ["https://www.w3.org/ns/activitystreams#Public"],
        "cc": [
            ap_url(
                reverse(
                    "activitypub:followers", kwargs={"username": video.owner.username}
                )
            )
        ],
        "type": "Video",
        **video_name(video),
        **video_duration(video),
        **video_uuid(video),
        **video_views(video),
        **video_transcoding(video),
        **video_comments(video),
        **video_download(video),
        **video_dates(video),
        **video_tags(video),
        **video_urls(video),
        **video_attributions(video),
        **video_sensitivity(video),
        **video_likes(video),
        **video_shares(video),
        **video_category(video),
        **video_state(video),
        **video_support(video),
        **video_preview(video),
        **video_live(video),
        **video_subtitles(video),
        **video_chapters(video),
        **video_licences(video),
        **video_language(video),
        **video_description(video),
        **video_icon(video),
    }


def video_name(video):
    return {"name": video.title}


def video_duration(video):
    """duration must fit the xsd:duration format
    https://www.w3.org/TR/xmlschema11-2/#duration
    """
    return {"duration": f"PT{video.duration}S"}


def video_uuid(video):
    """needed by peertube in version 4 exactly
    https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/helpers/custom-validators/activitypub/videos.ts#L76
    """
    return {"uuid": str(stable_uuid(video.id, version=4))}


def video_views(video):
    """needed by peertube"""
    return {"views": video.viewcount}


def video_transcoding(video):
    return {"waitTranscoding": video.encoding_in_progress}


def video_comments(video):
    """the comments endpoint is needed by peertube"""
    return {
        "commentsEnabled": not video.disable_comment,
        "comments": ap_url(
            reverse("activitypub:comments", kwargs={"slug": video.slug})
        ),
    }


def video_download(video):
    return {"downloadEnabled": video.allow_downloading}


def video_dates(video):
    """
    'published' and 'updated' are needed by peertube

    TODO: implement "originallyPublishedAt" when federation is implemented on pod side
    """
    return {
        "published": video.date_added.isoformat(),
        "updated": video.date_added.isoformat(),
    }


def video_tags(video):
    """tags (even empty) are needed by peertube
    https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/helpers/custom-validators/activitypub/videos.ts#L148-L157

    they may become fully optional someday
    https://framacolibri.org/t/comments-and-suggestions-on-the-peertube-activitypub-implementation/21215/2
    """
    return {
        "tag": [
            {"type": "Hashtag", "name": slugify(tag)} for tag in video.tags.split(" ")
        ],
    }


def video_urls(video):
    """
    peertube needs a matching magnet url for every mp4 url
    https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/lib/activitypub/videos/shared/object-to-model-attributes.ts#L61-L64

    magnets may become fully optional someday
    https://framacolibri.org/t/comments-and-suggestions-on-the-peertube-activitypub-implementation/21215/2
    """

    return {
        "url": (
            [
                # Webpage
                {
                    "type": "Link",
                    "mediaType": "text/html",
                    "href": ap_url(reverse("video:video", args=(video.slug,))),
                },
            ]
            + [
                # MP4 link
                {
                    "type": "Link",
                    "mediaType": mp4.encoding_format,
                    "href": ap_url(mp4.source_file.url),
                    "height": mp4.height,
                    "width": mp4.width,
                    "size": mp4.source_file.size,
                    # TODO: get the fps
                    # "fps": 30,
                }
                for mp4 in video.get_video_mp4()
            ]
            + [
                # Magnet
                {
                    "type": "Link",
                    "mediaType": "application/x-bittorrent;x-scheme-handler/magnet",
                    "href": make_magnet_url(video, mp4),
                    "height": mp4.height,
                    "width": mp4.width,
                    # TODO: get the fps
                    # "fps": 30,
                }
                for mp4 in video.get_video_mp4()
            ]
        )
    }


def video_attributions(video):
    """
    Group and Person attributions are needed by peertube
    TODO: ask peertube to make this optional
    https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/lib/activitypub/videos/shared/abstract-builder.ts#L47-L52

    This won't change soon
    https://framacolibri.org/t/comments-and-suggestions-on-the-peertube-activitypub-implementation/21215/2
    """

    return {
        "attributedTo": [
            # needed by peertube
            {
                "type": "Person",
                "id": ap_url(
                    reverse(
                        "activitypub:account", kwargs={"username": video.owner.username}
                    )
                ),
            },
            # We should fake a default channel for every videos
            {
                "type": "Group",
                "id": ap_url(
                    reverse(
                        "activitypub:account_channel",
                        kwargs={"username": video.owner.username},
                    )
                ),
            },
        ]
        + [
            {
                "type": "Group",
                "id": ap_url(
                    reverse("activitypub:channel", kwargs={"slug": channel.slug})
                ),
            }
            for channel in video.channel.all()
        ],
    }


def video_sensitivity(video):
    """needed by peertube

    This may become optional someday
    https://framacolibri.org/t/comments-and-suggestions-on-the-peertube-activitypub-implementation/21215/2
    """
    return {
        "sensitive": False,
    }


def video_likes(video):
    """like and dislikes urls are needed by peertube.

    They may become optional someday
    https://framacolibri.org/t/comments-and-suggestions-on-the-peertube-activitypub-implementation/21215/2
    """

    return {
        "likes": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
        "dislikes": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
    }


def video_shares(video):
    """shares url is needed by peertube.

    This may become optional someday
    https://framacolibri.org/t/comments-and-suggestions-on-the-peertube-activitypub-implementation/21215/2
    """

    return {
        "shares": ap_url(reverse("activitypub:likes", kwargs={"slug": video.slug})),
    }


def video_category(video):
    """
    we could use video.type as AP 'category'
    but peertube categories are fixed, and identifiers are expected to be integers
    https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/initializers/constants.ts#L544-L563
    example of expected content:
      "category": {"identifier": "11", "name": "News & Politics & shit"}
    """
    return {}


def video_state(video):
    """
    'state' is optional
    peertube valid values are
    https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/packages/models/src/videos/video-state.enum.ts#L1-L12C36
    """

    return {}


def video_support(video):
    """'support' is not managed by pod"""
    return {}


def video_preview(video):
    """'preview' thumbnails are not supported by pod"""
    return {}


def video_live(video):
    """
    Pod don't support live at the moment, so the following optional fields are ignored
    isLiveBroadcast, liveSaveReplay, permanentLive, latencyMode, peertubeLiveChat
    """
    return {}


def video_subtitles(video):
    has_tracks = video.track_set.all().count() > 0
    if not has_tracks:
        return {}

    return {
        "subtitleLanguage": [
            {
                "identifier": track.lang,
                "name": track.get_label_lang(),
                "url": ap_url(track.src.file.url),
            }
            for track in video.track_set.all()
        ]
    }


def video_chapters(video):
    has_chapters = video.chapter_set.all().count() > 0
    if not has_chapters:
        return {}

    return {
        "hasParts": ap_url(reverse("activitypub:chapters", kwargs={"slug": video.slug}))
    }


def video_licences(video):
    """
    peertube needs integers identifiers for licences
    https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/helpers/custom-validators/activitypub/videos.ts#L78

    This may become spdy identifiers like 'by-nd' someday
    https://framacolibri.org/t/comments-and-suggestions-on-the-peertube-activitypub-implementation/21215/2
    """

    reverse_license_mapping = {v: k for k, v in AP_LICENSE_MAPPING.items()}
    if not video.licence or video.licence not in reverse_license_mapping:
        return {}

    return {
        "licence": {
            "identifier": str(reverse_license_mapping[video.licence]),
            "name": video.get_licence(),
        }
    }


def video_language(video):
    if not video.main_lang:
        return {}

    return {
        "language": {
            "identifier": video.main_lang,
            "name": video.get_main_lang(),
        }
    }


def video_description(video):
    """
    peertube only supports one language
    TODO ask for several descriptions in several languages

    peertube only supports markdown
    https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/helpers/custom-validators/activitypub/videos.ts#L182

    text/html may be supported someday
    https://framacolibri.org/t/comments-and-suggestions-on-the-peertube-activitypub-implementation/21215/2
    This would allow Pod to avoid using markdownify
    """
    if not video.description:
        return {}

    return {
        "mediaType": "text/markdown",
        "content": markdownify(video.description),
    }


def video_icon(video):
    """
    # only image/jpeg is supported on peertube
    # https://github.com/Chocobozzz/PeerTube/blob/b824480af7054a5a49ddb1788c26c769c89ccc8a/server/core/helpers/custom-validators/activitypub/videos.ts#L192
    """
    if not video.thumbnail:
        return {}

    return {
        "icon": [
            {
                "type": "Image",
                "url": video.get_thumbnail_url(scheme=True),
                "width": video.thumbnail.file.width,
                "height": video.thumbnail.file.height,

                # TODO: use the real media type when peertub supports JPEG
                # "mediaType": video.thumbnail.file_type,
                "mediaType": "image/jpeg",
            },
        ]
    }
