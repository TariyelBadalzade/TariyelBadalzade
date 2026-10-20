# Your GitHub Data Science portfolio

This pack contains a profile README, a project plan, and a reusable project README template. It does not contain completed analyses or trained models. The profile README is published in this repository; the projects in the roadmap are planned.

## Publish your profile

1. Review `README.md` and adjust any experience or skill you do not want to present publicly.
2. On GitHub, create a public repository whose name exactly matches your GitHub username.
3. Put this pack's `README.md` at the root of that repository.
4. Optionally add your LinkedIn profile and public contact email.
5. Build separate repositories for your projects. Add links to the profile README when those repositories contain useful, reproducible work.
6. Use Customize your pins on your profile to feature your strongest repositories.

Profile README guide: https://docs.github.com/en/account-and-profile/how-tos/profile-customization/managing-your-profile-readme
Pinned repository guide: https://docs.github.com/en/account-and-profile/how-tos/profile-customization/pinning-items-to-your-profile

## What makes the portfolio useful

Start with three substantial projects. Give each a clear question, a documented dataset, a reproducible method, a baseline, evaluation, and an explanation of what the results mean. A reader should understand the project before opening a notebook.

For you, a good first set is:

1. Operational analytics: SQL and business understanding.
2. Energy forecasting: statistics, time series, and model evaluation.
3. Satellite flood segmentation: computer vision and geospatial AI.

These are proposed directions. Existing relevant work can replace them once its code, data rights, and results are reviewed.

## Suggested layout for each project

- `README.md`: problem, preview, method, results, limitations, and setup.
- `notebooks/`: exploration and documented experiments in execution order.
- `src/`: reusable preprocessing, training, or evaluation code when needed.
- `data/README.md`: source, terms, schema, and download instructions.
- `reports/figures/`: exported plots and screenshots referenced in the README.
- `requirements.txt`: dependencies and versions tested with the project.
- `.gitignore`: exclude secrets, local environments, restricted data, and large generated files.

Only create folders that have a purpose. Before publishing, run the documented workflow from a clean environment and check that all README links work.

## Publishing checklist

- State whether the project is planned, in progress, or complete.
- Explain your own contribution to team or internship work.
- Use public or appropriately licensed data; obtain permission before sharing employer code or data.
- Report measured results, including the baseline, evaluation split, and limitations.
- Avoid target leakage and fit learned preprocessing on the training split only.
- Add at least one meaningful result figure with a caption.
- Include exact setup and execution commands after the actual implementation exists.
- Choose a code license only when you have the right to license the code; document dataset terms separately.
