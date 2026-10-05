# Website maintenance

- Before adding or changing portfolio content, repository structure, or maintenance workflows, read .local/MAINTENANCE.md.
- Whenever project structure changes, update the affected directory trees, file paths, examples, and maintenance instructions in .local/MAINTENANCE.md as part of the same task. Keep the note consistent with the final implemented structure.
- The maintenance note is local-only. Do not commit or upload .local/, or copy private maintenance notes into the public README.md.
- Portfolio documents live in content/_<collection>/<slug>.md. Original assets live in assets/<collection>/<slug>/. Use the same stable slug for the document and asset folder; keep published page URLs stable.
- The user adds Markdown documents and original-size assets only. Keep original file bytes intact; do not require hand-authored thumbnails or srcset attributes. Reorganization may update paths, with existing original-asset URLs preserved by scripts/legacy_asset_paths.json.
- Image optimization is part of Jekyll's post-write hook in _plugins/optimize_images.rb. Use the normal build/serve commands without --safe so the hook runs. Generated assets belong only in _site/ and .image-cache/; do not commit them.
- When adding a project, include preview and image verification in the work without waiting for a separate user reminder.
- For image-pipeline changes, run python3 -m unittest discover -s scripts/tests -v and bundle exec jekyll build, and inspect the rendered image references and display.
