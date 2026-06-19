import os
import base64
from datetime import datetime, timezone
from io import BytesIO

from flask import (
    Flask, request, jsonify, render_template, send_file, abort
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

# ---------------------------------------------------------------------------
# App & Database configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Render provides DATABASE_URL for the managed PostgreSQL instance.
# Locally we fall back to a SQLite file so the app runs with zero setup.
database_url = os.environ.get("DATABASE_URL", "sqlite:///trades.db")
# SQLAlchemy needs the 'postgresql://' scheme (Render gives 'postgres://').
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = 12 * 1024 * 1024  # 12 MB max upload

db = SQLAlchemy(app)


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------
class Trade(db.Model):
    __tablename__ = "trades"

    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(40), nullable=False)
    direction = db.Column(db.String(10), nullable=False, default="LONG")  # LONG / SHORT
    entry_price = db.Column(db.Float, nullable=False)
    exit_price = db.Column(db.Float, nullable=True)
    quantity = db.Column(db.Float, nullable=False, default=1)
    status = db.Column(db.String(10), nullable=False, default="OPEN")  # OPEN / CLOSED
    trade_date = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    strategy = db.Column(db.String(80), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    # Image stored directly in the DB so it survives Render's ephemeral disk.
    image_data = db.Column(db.LargeBinary, nullable=True)
    image_mime = db.Column(db.String(60), nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # ---- helpers ----------------------------------------------------------
    @property
    def pnl(self):
        """Realised P&L for a closed trade, else None."""
        if self.status == "CLOSED" and self.exit_price is not None:
            diff = (self.exit_price - self.entry_price)
            if self.direction == "SHORT":
                diff = -diff
            return round(diff * self.quantity, 2)
        return None

    @property
    def pnl_pct(self):
        if self.status == "CLOSED" and self.exit_price is not None and self.entry_price:
            diff = (self.exit_price - self.entry_price) / self.entry_price * 100
            if self.direction == "SHORT":
                diff = -diff
            return round(diff, 2)
        return None

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "quantity": self.quantity,
            "status": self.status,
            "trade_date": self.trade_date.isoformat() if self.trade_date else None,
            "strategy": self.strategy,
            "notes": self.notes,
            "pnl": self.pnl,
            "pnl_pct": self.pnl_pct,
            "has_image": self.image_data is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


with app.app_context():
    db.create_all()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_float(value, default=None):
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_date(value):
    if not value:
        return datetime.now(timezone.utc)
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return datetime.now(timezone.utc)


def _apply_form_to_trade(trade, form, files):
    trade.symbol = (form.get("symbol") or trade.symbol or "").upper().strip()
    trade.direction = (form.get("direction") or trade.direction or "LONG").upper()
    trade.entry_price = _parse_float(form.get("entry_price"), trade.entry_price)
    trade.exit_price = _parse_float(form.get("exit_price"), None)
    trade.quantity = _parse_float(form.get("quantity"), trade.quantity or 1)
    trade.status = (form.get("status") or trade.status or "OPEN").upper()
    trade.strategy = form.get("strategy") or None
    trade.notes = form.get("notes") or None
    if form.get("trade_date"):
        trade.trade_date = _parse_date(form.get("trade_date"))

    # Image handling
    img = files.get("image")
    if img and img.filename:
        trade.image_data = img.read()
        trade.image_mime = img.mimetype or "image/png"
    elif form.get("remove_image") == "true":
        trade.image_data = None
        trade.image_mime = None
    return trade


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/trades", methods=["GET"])
def list_trades():
    q = Trade.query
    status = request.args.get("status")
    symbol = request.args.get("symbol")
    if status in ("OPEN", "CLOSED"):
        q = q.filter(Trade.status == status)
    if symbol:
        q = q.filter(Trade.symbol.ilike(f"%{symbol.strip()}%"))
    trades = q.order_by(Trade.trade_date.desc(), Trade.id.desc()).all()
    return jsonify([t.to_dict() for t in trades])


@app.route("/api/trades", methods=["POST"])
def create_trade():
    form = request.form
    if not form.get("symbol") or _parse_float(form.get("entry_price")) is None:
        return jsonify({"error": "symbol və entry_price tələb olunur"}), 400
    trade = Trade()
    _apply_form_to_trade(trade, form, request.files)
    db.session.add(trade)
    db.session.commit()
    return jsonify(trade.to_dict()), 201


@app.route("/api/trades/<int:trade_id>", methods=["GET"])
def get_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    return jsonify(trade.to_dict())


@app.route("/api/trades/<int:trade_id>", methods=["POST", "PUT"])
def update_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    _apply_form_to_trade(trade, request.form, request.files)
    db.session.commit()
    return jsonify(trade.to_dict())


@app.route("/api/trades/<int:trade_id>", methods=["DELETE"])
def delete_trade(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    db.session.delete(trade)
    db.session.commit()
    return jsonify({"deleted": trade_id})


@app.route("/api/trades/<int:trade_id>/image")
def trade_image(trade_id):
    trade = Trade.query.get_or_404(trade_id)
    if not trade.image_data:
        abort(404)
    return send_file(
        BytesIO(trade.image_data),
        mimetype=trade.image_mime or "image/png",
        download_name=f"trade_{trade_id}.png",
    )


@app.route("/api/stats")
def stats():
    closed = Trade.query.filter(Trade.status == "CLOSED").all()
    total = Trade.query.count()
    open_count = Trade.query.filter(Trade.status == "OPEN").count()

    pnls = [t.pnl for t in closed if t.pnl is not None]
    total_pnl = round(sum(pnls), 2) if pnls else 0
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    win_rate = round(len(wins) / len(pnls) * 100, 1) if pnls else 0
    avg_win = round(sum(wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(losses) / len(losses), 2) if losses else 0
    profit_factor = round(sum(wins) / abs(sum(losses)), 2) if losses and sum(losses) != 0 else None

    return jsonify({
        "total_trades": total,
        "open_trades": open_count,
        "closed_trades": len(closed),
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "wins": len(wins),
        "losses": len(losses),
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
    })


@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
