import json
from datetime import datetime
from typing import List
from loguru import logger
from library import render, readme, requirements


def write_files(csv_location: str, token_list: List[str], output_csv_filename: str, output_json_filename: str):
    start = datetime.now()

    # Read GitHub urls from google docs
    df_input = render.get_input_data(csv_location)
    # df_input = df_input.head(3)  # Testing
    # df_input = df_input.iloc[9:11]  # Testing

    # Augment repo name with metadata from GitHub
    logger.info(f"Processing {len(df_input)} records from {csv_location} with {len(token_list)=}...")
    df = render.process(df_input, token_list)

    # Write raw results to csv
    logger.info(f"Write raw results to csv...")
    df.to_csv(output_csv_filename)

    logger.info("Crawling readme files...")
    df["_readme_filename"] = df["_repopath"].apply(lambda x: readme.get_readme(x))

    # TODO: handle 'main' master branches also:
    df["_readme_giturl"] = df.apply(
        lambda row: f"https://raw.githubusercontent.com/{row['_repopath']}/master/{row['_readme_filename']}"
        if len(row["_readme_filename"]) > 0
        else "",
        axis=1,
    )

    # TODO: get from readme.get_readme above as tuple and zip as per
    #       https://stackoverflow.com/questions/16236684/apply-pandas-function-to-column-to-create-multiple-new-columns
    df["_readme_localurl"] = df.apply(
        lambda row: f"{row['_repopath'].replace('/', '~')}~{row['_readme_filename']}"
        if len(row["_readme_filename"]) > 0
        else "",
        axis=1,
    )

    logger.info("Crawling requirements files...")
    df["_requirements_filenames"] = df["_repopath"].apply(lambda x: requirements.get_requirements(x))

    # TODO: handle 'main' master branches also:
    df["_requirements_giturls"] = df.apply(
        lambda row: list(
            map(
                lambda x: f"https://raw.githubusercontent.com/{row['_repopath']}/master/{x}",
                row["_requirements_filenames"],
            )
        ),
        axis=1,
    )

    # TODO: get from readme.get_readme above as tuple and zip as per
    #       https://stackoverflow.com/questions/16236684/apply-pandas-function-to-column-to-create-multiple-new-columns
    df["_requirements_localurls"] = df.apply(
        lambda row: list(map(lambda x: f"{row['_repopath'].replace('/', '~')}~{x}", row["_requirements_filenames"])),
        axis=1,
    )

    # Write raw results to json table format (i.e. github_data.json)
    with open(output_json_filename, "w") as f:
        json_results = df.to_json(orient="table", double_precision=2)
        data = json.loads(json_results)
        json.dump(data, f, indent=4)

    # Write raw results to minimised json (i.e. github_data.min.json)
    output_minjson_filename = (
        output_json_filename.replace(".json", ".min.json")
        if ".json" in output_json_filename
        else output_json_filename + ".min.json"
    )
    with open(output_minjson_filename, "w") as f:
        json_results = df.to_json(orient="table", double_precision=2)
        data = json.loads(json_results)
        json.dump(data, f, separators=(",", ":"))

    # Write UI results to minimised json (i.e. github_data.ui.min.json)
    output_ui_minjson_filename = (
        output_json_filename.replace(".json", ".ui.min.json")
        if ".json" in output_json_filename
        else output_json_filename + ".ui.min.json"
    )
    with open(output_ui_minjson_filename, "w") as f:
        # NOTE: this cols list must be synced with app.js DataTable columns for display
        cols = ["githuburl", "_reponame", "_organization", "_homepage", "_pop_score", "_stars", "_stars_per_week",
                "_description", "_age_weeks", "category", "_topics", "_readme_localurl"]
        json_results = df[cols].to_json(orient="table", double_precision=2, index=False)
        data = json.loads(json_results)
        json.dump(data, f, separators=(",", ":"))

    # Add markdown columns for local README.md and categories/*.md file lists.
    logger.info(f"Add markdown columns...")
    df = render.add_markdown(df)

    # Write all results to README.md
    lines_footer = [
        f"This file was automatically generated on {datetime.now().date()}.  "
        f"\n\nTo curate your own github list, simply clone and change the input csv file.  "
        f"\n\nInspired by:  "
        f"\n[https://github.com/vinta/awesome-python](https://github.com/vinta/awesome-python)  "
        f"\n[https://github.com/trananhkma/fucking-awesome-python](https://github.com/trananhkma/fucking-awesome-python)  "
    ]
    lines = []
    lines.extend(render.lines_header(len(df)))
    lines.extend(list(df["_doclines_main"]))
    lines.extend(lines_footer)

    logger.info(f"Writing {len(df)} entries to README.md...")
    with open("README.md", "w") as out:
        out.write("\n".join(lines))

    # Write to categories file
    categories = df["category"].unique()
    for category in categories:
        df_category = df[df["category"] == category]
        lines = []
        lines.extend(render.lines_header(len(df_category), category))
        lines.extend(list(df_category["_doclines_child"]))
        lines.extend(lines_footer)
        filename = f"categories/{category}.md"
        logger.info(f"Writing {len(df_category)} entries to {filename}...")
        with open(filename, "w") as out:
            out.write("\n".join(lines))

    logger.info(f"Finished writing in {datetime.now() - start}")
