"""utils package — image processing, export, helpers, CSS."""

from utils.image_utils import (
    make_thumbnail,
    make_display_image,
    bytes_to_base64_img_tag,
    image_to_base64_str,
    get_image_info,
    is_valid_image_bytes,
    get_image_mime_type,
)
from utils.export_utils import (
    export,
    export_json,
    export_markdown,
    export_pdf,
    export_docx,
    export_txt,
)
from utils.helpers import (
    truncate,
    contains_json,
    contains_markdown_table,
    extract_code_blocks,
    strip_markdown,
    estimate_tokens,
    now_utc,
    format_timestamp,
    time_ago,
    ss_get,
    ss_set,
    ss_init,
    ss_delete,
    SSKey,
    document_type_badge,
    confidence_badge,
    spinner_html,
)
from utils.css_styles import get_main_css, get_loading_css

__all__ = [
    # image
    "make_thumbnail",
    "make_display_image",
    "bytes_to_base64_img_tag",
    "image_to_base64_str",
    "get_image_info",
    "is_valid_image_bytes",
    "get_image_mime_type",
    # export
    "export",
    "export_json",
    "export_markdown",
    "export_pdf",
    "export_docx",
    "export_txt",
    # helpers
    "truncate",
    "contains_json",
    "contains_markdown_table",
    "extract_code_blocks",
    "strip_markdown",
    "estimate_tokens",
    "now_utc",
    "format_timestamp",
    "time_ago",
    "ss_get",
    "ss_set",
    "ss_init",
    "ss_delete",
    "SSKey",
    "document_type_badge",
    "confidence_badge",
    "spinner_html",
    # css
    "get_main_css",
    "get_loading_css",
]
