import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from PIL import Image
import os

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
DAY_LABELS = ["MON", "TUE", "WED", "THU", "FRI"]
HOURS = list(range(8, 22))

MODULE_COLORS = [
    "#FF9999", "#66B3FF", "#99FF99", "#FFCC99", "#C2C2F0",
    "#FFB6C1", "#FFD700", "#87CEEB", "#90EE90", "#FFA07A"
]

def time_to_decimal(t):
    return int(t[:2]) + (0.5 if t[2:] == "30" else 0)

def draw_timetable(schedule, semester=1, acad_year="2025/2026", out_image="timetable.png", out_pdf="timetable.pdf"):
    fig, ax = plt.subplots(figsize=(16, 6))
    ax.set_xlim(0, len(HOURS))
    ax.set_ylim(0, len(DAYS))

    # Axes setup
    ax.set_xticks(range(len(HOURS)))
    ax.set_xticklabels([f"{int(h):02d}{'30' if h % 1 else '00'}" for h in HOURS])
    ax.set_yticks([i + 0.5 for i in range(len(DAYS))])
    ax.set_yticklabels(DAY_LABELS)
    ax.invert_yaxis()
    ax.grid(False)

    # Background stripes
    for i in range(len(DAYS)):
        ax.axhspan(i, i + 1, facecolor="#f9f9f9" if i % 2 == 0 else "#e9e9e9", zorder=0)

    # Light vertical lines
    for i, h in enumerate(HOURS):
        if h % 1 == 0:  # full hour
            ax.axvline(i, color="#dddddd", linewidth=0.6, zorder=1)

    module_colors = {}
    legend_handles = {}
    color_index = 0

    for entry in schedule:
        mod = entry["module"]
        if mod not in module_colors:
            module_colors[mod] = MODULE_COLORS[color_index % len(MODULE_COLORS)]
            color_index += 1
        color = module_colors[mod]

        for lesson in entry["lessons"]:
            if lesson["day"] not in DAYS:
                continue

            day_idx = DAYS.index(lesson["day"])
            start = time_to_decimal(lesson["startTime"])
            end = time_to_decimal(lesson["endTime"])
            x = HOURS.index(int(start))
            width = int(end - start)
            y = day_idx

            # Slight margin between boxes
            rect = plt.Rectangle(
                (x + 0.05, y + 0.05),
                width - 0.1,
                0.9,
                color=color,
                edgecolor="black",
                linewidth=1,
                zorder=2
            )
            ax.add_patch(rect)

            # Label inside
            label = f"{mod}\n{lesson['lessonType']} [{lesson['classNo']}]\n{lesson['venue']}"
            if "weeks" in lesson:
                weeks = lesson["weeks"]
                if isinstance(weeks, list):
                    if len(weeks) == 1:
                        label += f"\nWeek {weeks[0]}"
                    else:
                        label += f"\nWeeks {weeks[0]}–{weeks[-1]}"
            ax.text(
                x + width / 2,
                y + 0.5,
                label,
                ha="center",
                va="center",
                fontsize=7.5,
                wrap=True,
                zorder=3
            )

            legend_handles[mod] = color

    # Title
    ax.set_title(f"AY{acad_year} Semester {semester}", fontsize=14, pad=20)

    # Legend
    legend_patches = [Patch(facecolor=c, edgecolor='black', label=m) for m, c in legend_handles.items()]
    ax.legend(handles=legend_patches, title="Modules", bbox_to_anchor=(1.01, 1), loc="upper left")

    plt.tight_layout()
    fig.savefig(out_image, bbox_inches="tight")
    plt.close()

    # Save as PDF
    img = Image.open(out_image).convert("RGB")
    img.save(out_pdf)

    return out_image, out_pdf
