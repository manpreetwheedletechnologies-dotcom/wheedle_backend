from flask import Blueprint, request, jsonify
from ..middleware.auth import token_required
from ..db import mongo
from ..utils.serializer import serialize_docs

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard', methods=['GET'])
@token_required
def dashboard(current_user):
    """
    Admin dashboard overview.
    Returns counts + recent live chats so the frontend can display them.
    """
    # ── counts ────────────────────────────────────────────────────────────────
    total_leads      = mongo.db.leads.count_documents({})
    total_form_leads = mongo.db.formleads.count_documents({})
    total_contacts   = mongo.db.contacts.count_documents({})
    total_blogs      = mongo.db.blogs.count_documents({})
    total_jobs       = mongo.db.jobs.count_documents({})

    # ── live chat counts ──────────────────────────────────────────────────────
    open_chats   = mongo.db.live_chats.count_documents({"status": "open"})
    closed_chats = mongo.db.live_chats.count_documents({"status": "closed"})
    total_chats  = open_chats + closed_chats

    # ── recent live chats (last 20, newest first) ─────────────────────────────
    recent_chats_cursor = (
        mongo.db.live_chats
        .find({})
        .sort("updated_at", -1)
        .limit(20)
    )
    recent_chats = serialize_docs(list(recent_chats_cursor))

    return jsonify({
        'message':        'Welcome Admin Dashboard',
        'adminId':        str(current_user['_id']),
        'counts': {
            'leads':       total_leads,
            'formLeads':   total_form_leads,
            'contacts':    total_contacts,
            'blogs':       total_blogs,
            'jobs':        total_jobs,
            'openChats':   open_chats,
            'closedChats': closed_chats,
            'totalChats':  total_chats,
        },
        'recentChats': recent_chats,
    })


@dashboard_bp.route('/dashboard/live-chats', methods=['GET'])
@token_required
def get_live_chats(current_user):
    """
    All live chat sessions, newest first.
    Optional ?status=open or ?status=closed
    """
    status_filter = request.args.get('status')
    query = {}
    if status_filter in ('open', 'closed'):
        query['status'] = status_filter

    chats = list(mongo.db.live_chats.find(query).sort("updated_at", -1))
    return jsonify(serialize_docs(chats))


@dashboard_bp.route('/dashboard/live-chats/<chat_id>', methods=['GET'])
@token_required
def get_live_chat_detail(current_user, chat_id):
    """Single chat session with full message history."""
    from bson import ObjectId
    from ..utils.serializer import serialize_doc
    try:
        doc = mongo.db.live_chats.find_one({"_id": ObjectId(chat_id)})
    except Exception:
        return jsonify({"error": "Invalid chat_id"}), 400
    if not doc:
        return jsonify({"error": "Chat not found"}), 404
    return jsonify(serialize_doc(doc))
