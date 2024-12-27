from flask import Blueprint, jsonify, request, current_app
from werkzeug.utils import secure_filename
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import os
import json



from models import db, Company, Workspace, File, Report, Dashboard, Chart

workspace_bp = Blueprint('workspace', __name__, url_prefix='/workspace')

@workspace_bp.route('/all', methods=['GET'])
@jwt_required()
def get_workspaces():
    print("working")
    dict = json.loads(get_jwt_identity())
    company_id = dict['id']
    workspaces = Workspace.query.filter_by(company_id=company_id).all()
    workspaces_list = [{
        'id': ws.id,
        'name': ws.name,
        'description': ws.description,
        'created_on': ws.created_on.isoformat(),
        'image_file_path': ws.image_file_path
    } for ws in workspaces]
    return jsonify({'workspaces': workspaces_list})

@workspace_bp.route('/<int:workspace_id>', methods=['GET'])
@jwt_required()
def get_workspace_details(workspace_id):
    dict = json.loads(get_jwt_identity())
    company_id = dict['id']
    company_workspaces = Workspace.query.filter_by(company_id=company_id).all()
    workspace = Workspace.query.get_or_404(workspace_id)
    if workspace not in company_workspaces:
        return jsonify({"error":"You don't have permission to see details of this workspace"}), 400
    files = File.query.filter_by(workspace_id=workspace_id).all()
    reports = Report.query.filter_by(workspace_id=workspace_id).all()
    dashboards = Dashboard.query.filter_by(workspace_id=workspace_id).all()
    charts = Chart.query.filter_by(workspace_id=workspace_id).all()
    response = {
        'workspace': {
            'id': workspace.id,
            'name': workspace.name,
            'description': workspace.description,
            'created_on': workspace.created_on.isoformat(),
            'image_file_path': workspace.image_file_path
        },
        'files': [{'id': file.id, 'filename': file.filename, 'file_path': file.file_path} for file in files],
        'reports': [{'id': report.id, 'name': report.name} for report in reports],
        'dashboards': [{'id': dashboard.id, 'name': dashboard.name} for dashboard in dashboards],
        'charts': [{'id': chart.id, 'name': chart.name} for chart in charts]
    }
    return jsonify(response)

@workspace_bp.route('/add_workspace', methods=['POST'])
@jwt_required()
def create_workspace():
    try:
        dict = json.loads(get_jwt_identity())
        company_id = dict['id']
        current_user = Company.query.filter_by(id=company_id).first()
        data = request.form
        title = data.get('title')
        description = data.get('description')
        image = request.files.get('image')
        datafile = request.files.get('datafile')

        if not title or not image or not datafile:
            return jsonify({'error': 'Title, image, and datafile are required'}), 400

        image_filename = secure_filename(image.filename)
        datafile_filename = secure_filename(datafile.filename)
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image_filename)
        datafile_path = os.path.join(current_app.config['UPLOAD_FOLDER'], datafile_filename)

        image.save(image_path)
        datafile.save(datafile_path)

        new_workspace = Workspace(
            name=title,
            description=description,
            image_file_path=image_path,
            company_id=current_user.id,
            created_on=datetime.utcnow()
        )
        db.session.add(new_workspace)
        db.session.commit()

        data_file = File(filename=datafile_filename, file_path=datafile_path, workspace_id=new_workspace.id)
        db.session.add(data_file)
        db.session.commit()

        return jsonify({'message': 'Workspace created successfully', 'workspace_id': new_workspace.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@workspace_bp.route('/dummy', methods=['GET'])
@jwt_required()
def isworking():
    return "yes working"

@workspace_bp.route('/delete/<int:workspace_id>', methods=['DELETE'])
@jwt_required()
def delete_workspace(workspace_id):
    try:
        dict = json.loads(get_jwt_identity())
        company_id = dict['id']
        company_workspaces = Workspace.query.filter_by(company_id=company_id).all()
        workspace = Workspace.query.get(workspace_id)
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        if workspace not in company_workspaces:
            return jsonify({"error":"You don't have permission to see details of this workspace"}), 400

        for file in workspace.files:
            db.session.delete(file)

        for report in workspace.reports:
            db.session.delete(report)

        for dashboard in workspace.dashboards:
            db.session.delete(dashboard)

        charts = Chart.query.filter_by(workspace_id=workspace.id).all()
        for chart in charts:
            db.session.delete(chart)

        db.session.delete(workspace)
        db.session.commit()

        return jsonify({'message': 'Workspace and related data deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


