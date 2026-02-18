def ast_to_text(node, prefix="", is_last=True, is_root=False):
    if node is None:
        return ""

    lines = []

    if is_root:
        lines.append(type(node).__name__)
        child_prefix = ""
    else:
        branch = "└── " if is_last else "├── "
        lines.append(prefix + branch + type(node).__name__)
        child_prefix = prefix + ("    " if is_last else "│   ")

    if not hasattr(node, "__dict__"):
        return "\n".join(lines)

    children = []

    for key, value in vars(node).items():

        if value is None:
            continue

        if isinstance(value, (str, int, float, tuple)):
            children.append(("attr", f"{key}: {value!r}"))

        elif isinstance(value, list) and value:
            children.append(("label", key))
            for item in value:
                if hasattr(item, "__dict__"):
                    children.append(("node", item))

        elif hasattr(value, "__dict__"):
            children.append(("label", key))
            children.append(("node", value))

    total = len(children)
    for idx, child in enumerate(children):
        last = idx == total - 1

        if child[0] == "attr":
            branch = "└── " if last else "├── "
            lines.append(child_prefix + branch + child[1])

        elif child[0] == "label":
            branch = "└── " if last else "├── "
            lines.append(child_prefix + branch + child[1] + ":")

        elif child[0] == "node":
            lines.append(
                ast_to_text(
                    child[1],
                    child_prefix,
                    last
                )
            )

    return "\n".join(lines)
