from difflib import SequenceMatcher

from .models import ChangeType, DiffEntry


class LineDiffStrategy:
    """Default strategy: compares texts line by line using the standard library."""

    name = "line"

    def diff(self, old: str, new: str) -> tuple[DiffEntry, ...]:
        old_lines, new_lines = old.splitlines(), new.splitlines()
        matcher = SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
        entries: list[DiffEntry] = []

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for offset in range(i2 - i1):
                    entries.append(self._unchanged(old_lines, new_lines, i1 + offset, j1 + offset))
                continue

            # "replace" pairs lines up as modifications; leftovers are plain removals/additions.
            paired = min(i2 - i1, j2 - j1) if tag == "replace" else 0
            for offset in range(paired):
                entries.append(
                    DiffEntry(
                        ChangeType.MODIFIED,
                        old_line=i1 + offset + 1,
                        new_line=j1 + offset + 1,
                        old_text=old_lines[i1 + offset],
                        new_text=new_lines[j1 + offset],
                    )
                )
            for i in range(i1 + paired, i2):
                entries.append(
                    DiffEntry(ChangeType.REMOVED, old_line=i + 1, old_text=old_lines[i])
                )
            for j in range(j1 + paired, j2):
                entries.append(DiffEntry(ChangeType.ADDED, new_line=j + 1, new_text=new_lines[j]))

        return tuple(entries)

    @staticmethod
    def _unchanged(old_lines: list[str], new_lines: list[str], i: int, j: int) -> DiffEntry:
        return DiffEntry(
            ChangeType.UNCHANGED,
            old_line=i + 1,
            new_line=j + 1,
            old_text=old_lines[i],
            new_text=new_lines[j],
        )
