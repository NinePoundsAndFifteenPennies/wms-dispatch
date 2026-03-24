from pathlib import Path


class AgentSkillLoader:
    _cache: dict[tuple[str, ...], str] = {}

    @staticmethod
    def _skills_dir() -> Path:
        return Path(__file__).resolve().parent / "Skills"

    @classmethod
    def load_skills(cls, names: list[str]) -> str:
        cache_key = tuple(names)
        cached = cls._cache.get(cache_key)
        if cached is not None:
            return cached

        chunks: list[str] = []
        skills_dir = cls._skills_dir()

        for name in names:
            path = skills_dir / name
            if not path.exists():
                raise RuntimeError(f"Required skill file is missing: {path}")
            content = path.read_text(encoding="utf-8").strip()
            chunks.append(f"[Skill: {name}]\n{content}")

        merged = "\n\n".join(chunks)
        cls._cache[cache_key] = merged
        return merged
