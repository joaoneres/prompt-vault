# Commands (asynchronous; they reply only when the sender provides a reply subject)
PROMPT_CREATE = "prompt.create"
PROMPT_VERSION_CREATE = "prompt.version.create"
PROMPT_CONTENT_UPDATE = "prompt.content.update"
PROMPT_VERSION_ACTIVATE = "prompt.version.activate"
PROMPT_DELETE = "prompt.delete"
PROMPT_RESTORE = "prompt.restore"

# Queries (request/reply)
PROMPT_GET = "prompt.get"
PROMPT_VERSIONS_LIST = "prompt.versions.list"
PROMPT_LIST_ACTIVE = "prompt.list.active"
PROMPT_LIST_DELETED = "prompt.list.deleted"
PROMPT_VERSIONS_COMPARE = "prompt.versions.compare"

# Outbound
EVENTS_PREFIX = "prompt.events"
ERRORS = "prompt.errors"
