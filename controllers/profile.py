from flask import Blueprint, jsonify, request, render_template, session, redirect, url_for, abort, Response
from controllers.auth import login_required
from models.profile import (
    add_profile,
    list_profiles,
    get_full_profile,
    get_photo_blob,
    reset_to_pending,
    delete_profile,
)
from services.scraper import scrape_in_background

profile_bp = Blueprint("profile", __name__)

LINKEDIN_PREFIX = "https://www.linkedin.com/in/"


def _get_url_from_body():
    body = request.get_json(silent=True) or {}
    url = body.get("url") or ""
    return url.strip()


@profile_bp.route("/")
@login_required
def index():
    return render_template("index.html", username=session.get("username", ""))


@profile_bp.route("/profile")
@login_required
def view_profile():
    url = request.args.get("url", "").strip()
    if not url:
        return redirect(url_for("profile.index"))

    data = get_full_profile(url)
    if not data:
        return redirect(url_for("profile.index"))

    return render_template(
        "profile_view.html",
        profile=data,
        url=url,
        username=session.get("username", ""),
    )


@profile_bp.route("/api/profiles", methods=["GET"])
@login_required
def api_list_profiles():
    return jsonify(list_profiles())


@profile_bp.route("/api/profiles", methods=["POST"])
@login_required
def api_add_profile():
    url = _get_url_from_body()
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400
    if not url.startswith(LINKEDIN_PREFIX):
        return jsonify({"error": "URL must be a LinkedIn profile URL"}), 400

    add_profile(url)
    scrape_in_background(url)
    return jsonify({"status": "pending", "url": url}), 201


@profile_bp.route("/api/profiles", methods=["DELETE"])
@login_required
def api_delete_profile():
    url = _get_url_from_body() or request.args.get("url", "").strip()
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400
    delete_profile(url)
    return jsonify({"deleted": url})


@profile_bp.route("/api/profiles/photo", methods=["GET"])
@login_required
def api_profile_photo():
    url = request.args.get("url", "").strip()
    if not url:
        abort(400)

    blob, ctype = get_photo_blob(url)
    if blob is None:
        abort(404)

    resp = Response(blob, mimetype=ctype)
    resp.headers["Cache-Control"] = "private, max-age=86400"
    return resp


@profile_bp.route("/api/profiles/refresh", methods=["POST"])
@login_required
def api_refresh_profile():
    url = _get_url_from_body()
    if not url:
        return jsonify({"error": "Missing 'url'"}), 400

    reset_to_pending(url)
    scrape_in_background(url)
    return jsonify({"status": "pending", "url": url})
