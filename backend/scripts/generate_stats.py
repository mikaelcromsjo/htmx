import sys, os, argparse, datetime
import plotly.graph_objects as go
from plotly.offline import plot
from sqlalchemy import func, case, cast, Integer
from sqlalchemy.orm import Session
import json

# --- Path setup (same as your manage_users.py) ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.database import SessionLocal
from models.models import Call, Customer, Event, EventCustomer, Caller

# -----------------------------
# MULTI-LANGUAGE SUPPORT (Swedish default)
# -----------------------------
LANG = {
    "en": {
        "calls_over_time": "📞 Calls Over Time",
        "caller_performance": "📊 Caller Performance",
        "event_participation": "🎟️ Event Participation",
        "no_call_data": "No call data found for given filters.",
        "no_event_data": "No event participation data found.",
        "x_date": "Date",
        "x_caller": "Caller",
        "x_event": "Event",
        "y_calls": "Number of Calls",
        "y_customers": "Number of Customers",
        "total_all": "Total (All Callers)",
        "statuses": {
            "answered": "Answered",
            "no_answer": "No Answer",
            "outside": "Outside System",
            "total": "Total",
            "not_interested": "Not Interested",
            "interested": "Interested",
            "comming": "Comming",
            "paid": "Paid",
            "attended": "Attended",
        },
    },
    "sv": {
        "calls_over_time": "📞 Samtal över tid",
        "caller_performance": "📊 Uppringar­prestation",
        "event_participation": "🎟️ Evenemangs­deltagande",
        "no_call_data": "Inga samtalsdata hittades för givna filter.",
        "no_event_data": "Ingen evenemangsdata hittades.",
        "x_date": "Datum",
        "x_caller": "Uppringare",
        "x_event": "Evenemang",
        "y_calls": "Antal samtal",
        "y_customers": "Antal kunder",
        "total_all": "Totalt (alla uppringare)",
        "statuses": {
            "answered": "Svarade",
            "no_answer": "Inget svar",
            "outside": "Utanför systemet",
            "total": "Totalt",
            "not_interested": "Ej intresserad",
            "interested": "Intresserad",
            "comming": "Kommer",
            "paid": "Betalat",
            "attended": "Deltagit",
        },
    },
}

# -----------------------------
# ARGUMENT PARSING
# -----------------------------
def parse_args():
    parser = argparse.ArgumentParser(description="Generate Call Center Statistics (HTML/Plotly)")
    parser.add_argument("--from", dest="date_from", required=False, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--to", dest="date_to", required=False, help="End date (YYYY-MM-DD)")
    parser.add_argument("--caller", help="Filter by caller name")
    parser.add_argument("--event-type", choices=["type_a", "type_b", "type_c", "type_d"], help="Filter events by type")
    parser.add_argument("--chart", choices=[
        "calls_over_time",
        "caller_performance",
        "event_participation",
    ], required=True)
#    parser.add_argument("--save", help="Path to save the HTML file", default="/app/backend/core/static/output.html")
    parser.add_argument("--lang", choices=["sv", "en"], default="sv", help="Språk / Language (sv or en)")
    return parser.parse_args()


def get_session() -> Session:
    return SessionLocal()


# -----------------------------
# HELPER: Save chart as HTML
# -----------------------------
def save_html(fig: go.Figure, filepath: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    plot(fig, filename=filepath, auto_open=False)
    print(f"✅ Saved interactive chart → static/output.html")

# -----------------------------
# CHARTS
# -----------------------------
def calls_over_time(session: Session, date_from, date_to, caller_name, lang):
    base_query = (
        session.query(
            func.date(Call.call_date).label("day"),
            func.count(Call.id).label("count"),
            Caller.name.label("caller_name"),
        )
        .join(Caller, Caller.id == Call.caller_id)
        .filter(Call.call_date.between(date_from, date_to))
        .group_by("day", "caller_name")
        .order_by("day")
    )

    if caller_name and caller_name.lower() != "all":
        base_query = base_query.filter(Caller.name == caller_name)

    data = base_query.all()
    if not data:
        print(lang["no_call_data"])
        return None

    caller_map = {}
    for row in data:
        caller_map.setdefault(row.caller_name, []).append((row.day, row.count))

    total_map = {}
    for row in data:
        total_map[row.day] = total_map.get(row.day, 0) + row.count
    total_days = sorted(total_map.keys())
    total_counts = [total_map[d] for d in total_days]

    fig = go.Figure()

    for cname, entries in caller_map.items():
        entries.sort(key=lambda x: x[0])
        days = [e[0] for e in entries]
        counts = [e[1] for e in entries]
        fig.add_trace(go.Scatter(x=days, y=counts, mode="lines+markers", name=cname, line=dict(width=2)))

    if not caller_name or caller_name.lower() == "all":
        fig.add_trace(
            go.Scatter(
                x=total_days,
                y=total_counts,
                mode="lines+markers",
                name=lang["total_all"],
                line=dict(width=4, color="black", dash="dash"),
            )
        )

    title_suffix = (
        f"({caller_name})" if caller_name and caller_name.lower() != "all" else f"({lang['total_all']})"
    )

    fig.update_layout(
        title=f"{lang['calls_over_time']} {title_suffix}<br><sup>{date_from.date()} → {date_to.date()}</sup>",
        xaxis_title=lang["x_date"],
        yaxis_title=lang["y_calls"],
        template="plotly_white",
        legend_title=lang["x_caller"],
        height=600,
    )

    return fig


def caller_performance(session: Session, date_from, date_to, lang):
    query = (
        session.query(
            Caller.name.label("caller_name"),
            func.sum(case((Call.status == 1, 1), else_=0)).label("answered"),
            func.sum(case((Call.status == 2, 1), else_=0)).label("no_answer"),
            func.sum(case((Call.status == 3, 1), else_=0)).label("outside"),
            func.count(Call.id).label("total"),
        )
        .join(Caller, Caller.id == Call.caller_id)
        .filter(Call.call_date.between(date_from, date_to))
        .group_by(Caller.name)
        .order_by(Caller.name)
    )

    data = query.all()
    if not data:
        print(lang["no_call_data"])
        return None

    names = [row.caller_name for row in data]
    answered = [row.answered for row in data]
    no_answer = [row.no_answer for row in data]
    outside = [row.outside for row in data]
    totals = [row.total for row in data]

    fig = go.Figure()
    fig.add_bar(name=lang["statuses"]["answered"], x=names, y=answered, marker_color="#5cb85c")
    fig.add_bar(name=lang["statuses"]["no_answer"], x=names, y=no_answer, marker_color="#d9534f")
    fig.add_bar(name=lang["statuses"]["outside"], x=names, y=outside, marker_color="#f0ad4e")
    fig.add_bar(name=lang["statuses"]["total"], x=names, y=totals, marker_color="#5bc0de")

    fig.update_layout(
        barmode="group",
        title=f"{lang['caller_performance']}<br><sup>{date_from.date()} → {date_to.date()}</sup>",
        xaxis_title=lang["x_caller"],
        yaxis_title=lang["y_calls"],
        template="plotly_white",
        legend=dict(title="Status"),
        height=600,
    )

    return fig


def event_participation(session: Session, date_from, date_to, event_type, caller_name, lang):
    base_query = (
        session.query(
            Event.name.label("event_name"),
            Caller.name.label("caller_name"),
            func.sum(case((EventCustomer.status == 1, 1), else_=0)).label("not_interested"),
            func.sum(case((EventCustomer.status == 2, 1), else_=0)).label("interested"),
            func.sum(case((EventCustomer.status == 3, 1), else_=0)).label("comming"),
            func.sum(case((EventCustomer.status == 4, 1), else_=0)).label("paid"),
            func.sum(case((EventCustomer.status == 5, 1), else_=0)).label("attended"),
        )
        .join(Event, Event.id == EventCustomer.event_id)
        .join(Customer, Customer.id == EventCustomer.customer_id)
        .join(Caller, Caller.id == Customer.caller_id)
        .filter(Event.start_date.between(date_from, date_to))
        .group_by(Event.name, Caller.name)
        .order_by(Event.start_date)
    )

    if caller_name and caller_name.lower() != "all":
        base_query = base_query.filter(Caller.name == caller_name)

    if event_type:
        base_query = base_query.filter(getattr(Event, event_type) == True)

    data = base_query.all()
    if not data:
        print(lang["no_event_data"])
        return None

    callers = sorted({row.caller_name for row in data})
    events = sorted({row.event_name for row in data})
    categories = ["not_interested", "interested", "comming", "paid", "attended"]
    colors = {
        "not_interested": "#d9534f",
        "interested": "#f0ad4e",
        "comming": "#de7e5b",
        "paid": "#5bc0de",
        "attended": "#5cb85c",
    }

    stats = {c: {e: {cat: 0 for cat in categories} for e in events} for c in callers}
    for row in data:
        for cat in categories:
            stats[row.caller_name][row.event_name][cat] = getattr(row, cat) or 0

    total = {e: {cat: 0 for cat in categories} for e in events}
    for e in events:
        for c in callers:
            for cat in categories:
                total[e][cat] += stats[c][e][cat]

    fig = go.Figure()

    for idx, caller in enumerate(callers):
        for cat in categories:
            hover_text = [
                f"{lang['x_event']}: {e}<br>{lang['x_caller']}: {caller}<br>{lang['statuses'][cat]}: {stats[caller][e][cat]}"
                for e in events
            ]
            fig.add_bar(
                name=lang["statuses"][cat],   # ✅ visar rätt namn i legend / footer
                x=events,
                y=[stats[caller][e][cat] for e in events],
                marker_color=colors[cat],
                offsetgroup=idx,
                legendgroup=cat,
                showlegend=(idx == 0),  # visar bara en gång per kategori
                opacity=0.85,
                hovertext=hover_text,
                hoverinfo="text",
            )

    for cat in categories:
        hover_text = [
            f"{lang['x_event']}: {e}<br>{lang['statuses'][cat]}: {total[e][cat]}"
            for e in events
        ]
        fig.add_bar(
            name=f"{lang['statuses'][cat]} ({lang['total_all']})",
            x=events,
            y=[total[e][cat] for e in events],
            marker_color=colors[cat],
            offsetgroup="total",
            legendgroup="Total",
            showlegend=False,
            opacity=1.0,
            marker_line=dict(width=1.5, color="black"),
            hovertext=hover_text,
            hoverinfo="text",
        )

    title_suffix = (
        f"({caller_name})" if caller_name and caller_name.lower() != "all" else f"({lang['total_all']})"
    )

    fig.update_layout(
        barmode="stack",
        title=f"{lang['event_participation']} {title_suffix}<br><sup>{date_from.date()} → {date_to.date()}</sup>",
        xaxis_title=lang["x_event"],
        yaxis_title=lang["y_customers"],
        template="plotly_white",
        height=750,
        legend=dict(title=lang["x_caller"], orientation="h", y=-0.2),
        bargap=0.25,
    )

    return fig


# -----------------------------
# MAIN ENTRYPOINT
# -----------------------------
def main():
    args = parse_args()
    lang = LANG[args.lang]

    START_OF_TIME = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    END_OF_TIME = datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)

    date_from = (
        datetime.datetime.fromisoformat(args.date_from)
        if getattr(args, "date_from", None)
        else START_OF_TIME
    )
    date_to = (
        datetime.datetime.fromisoformat(args.date_to)
        if getattr(args, "date_to", None)
        else END_OF_TIME
    )

    session = get_session()
    try:
        if args.chart == "calls_over_time":
            fig = calls_over_time(session, date_from, date_to, args.caller, lang)
        elif args.chart == "caller_performance":
            fig = caller_performance(session, date_from, date_to, lang)
        elif args.chart == "event_participation":
            fig = event_participation(session, date_from, date_to, args.event_type, args.caller, lang)
        else:
            print(f"Chart '{args.chart}' not implemented.")
            return


        if fig:
            output_path = "/app/backend/core/static/output.html"
            save_html(fig, output_path)
            print(json.dumps({"html_created": True, "output_path": "/static/output.html"}))
        else:
            print(json.dumps({"html_created": False}))            


    finally:
        session.close()


if __name__ == "__main__":
    main()
