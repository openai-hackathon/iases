"""Small authoring vocabulary; all expected outputs are specified independently."""

from dataclasses import dataclass
from textwrap import dedent


@dataclass(frozen=True)
class Case:
    name: str
    request: dict
    expected: object = None
    error: str | None = None
    public: bool = False


@dataclass(frozen=True)
class Change:
    path: str
    before: str
    after: str

    def apply(self, files):
        files = dict(files)
        if files[self.path].count(self.before) != 1:
            raise ValueError(
                f"Mutation must match exactly once: {self.path}: {self.before!r}"
            )
        files[self.path] = files[self.path].replace(self.before, self.after, 1)
        return files


@dataclass(frozen=True)
class Task:
    task_id: str
    title: str
    difficulty: str
    family: str
    contract: str
    files: dict[str, str]
    faults: tuple[Change, ...]
    mutants: dict[str, tuple[Change, ...]]
    cases: tuple[Case, ...]
    references: tuple[str, ...] = ()
    extra_public_tests: str = ""
    extra_hidden_tests: str = ""
    difficulty_reason: str = ""
    version: str = "1.0"


def code(text):
    return dedent(text).strip() + "\n"


def simple(
    task_id,
    title,
    family,
    contract,
    implementation,
    fault,
    mutants,
    cases,
    references=(),
    difficulty="easy",
    difficulty_reason="",
):
    return Task(
        task_id,
        title,
        difficulty,
        family,
        contract,
        {"fabops/domain.py": code(implementation)},
        (Change("fabops/domain.py", *fault),),
        {
            name: (Change("fabops/domain.py", *change),)
            for name, change in mutants.items()
        },
        tuple(cases),
        tuple(references),
        difficulty_reason=difficulty_reason,
    )
