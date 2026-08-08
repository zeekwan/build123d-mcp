# Output

Finished CAD exports, one subdirectory per project:

```
output/
└── <project-name>/
    ├── <part>.step
    └── <part>.3mf
```

Committed to git so `git fetch && git reset --hard origin/mine` on another machine pulls the finished files too. Create a new subdirectory per project as you go — no tooling needed, just `git add personal/output/<project>/...`.
