from analysis import build_report
from telegram_bot import send_message

def main():
    market, direction, score, rows, headlines, high = build_report()

    lines = [
        "📡 CRYPTOSCOPE AI",
        "",
        f"MARKET: {direction}",
        f"SCORE: {score}",
        f"BTC DOMINANCE: {market.get('btc_dominance')}%",
        "",
        "MARKET FACTORS:"
    ]

    for name, value in rows:
        lines.append(f"{name}: {value}")

    lines.append("")
    lines.append("IMPORTANT NEWS:")

    if high:
        for item in high[:5]:
            lines.append(
                f"\n{item['score']}/100 - {item['title']}\n{item['url']}"
            )
    else:
        lines.append("No critical news found.")

    send_message("\n".join(lines))

if __name__ == "__main__":
    main()
