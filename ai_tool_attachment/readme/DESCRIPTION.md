Provides a `read_attachment` AI tool and a generic file representation
(`_to_ai_file()`) for passing attachments to AI connections.

- `ir.attachment._to_ai_file()` converts any attachment to a
  provider-agnostic file dict with type, mimetype, base64 data.
- `read_attachment` AI tool lets agents read attachment content
  by ID or by record (model + res_id).
- Supports text, PDF, DOCX, images, and audio files.
