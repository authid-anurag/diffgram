from methods.regular.regular_api import *
from shared.database.action.action import Action
from shared.database.action.workflow import Workflow


@routes.route('/api/v1/project/<string:project_string_id>' +
              '/actions/workflow/update',
              methods=['PUT'])
@Project_permissions.user_has_project(
    Roles=["admin", "Editor"],
    apis_user_list=['api_enabled_builder', 'security_email_verified'])
@limiter.limit("20 per day")
def api_workflow_update(project_string_id):
    """
    TODO maybe prefer to pass whole flow object?

    """

    spec_list = [
        {'workflow_id': int},
        {'name': str},
        {'trigger_type': str},
        {'mode': str},
        {'active': bool},
        {'time_window':{
            'default': '1_minute',
            'kind': str,
            'required': False
        }},

    ]

    log, input, untrusted_input = regular_input.master(request=request,
                                                       spec_list=spec_list)
    if len(log["error"].keys()) >= 1:
        return jsonify(log=log), 400

    with sessionMaker.session_scope() as session:

        user = User.get(session=session)
        project = Project.get(session, project_string_id)

        flow = Workflow.get_by_id(
            session=session,
            id=input['workflow_id'],
            project_id=project.id)

        if flow is None:
            log['error']['flow'] = "No Flow found"
            return jsonify(log=log), 400

        log = flow_update_core(
            session=session,
            project=project,
            flow=flow,
            name=input['name'],
            trigger_type=input['trigger_type'],
            time_window=input.get('time_window', None),
            active=input['active'],
            mode=input['mode'],
            log=log,
            member=user.member)

        if len(log["error"].keys()) >= 1:
            return jsonify(log=log), 400

        log['success'] = True
        return jsonify(
            flow=flow.serialize(),
            log=log), 200


def flow_update_core(
        session,
        project,
        flow,
        name,
        active,
        trigger_type,
        time_window,
        mode,
        log,
        member):
    if mode == "ARCHIVE":
        flow.archived = True
        flow.active = False
        session.add(flow)

        return log

    if mode == "UPDATE":
        session.add(flow)

        flow.is_new = False

        flow.name = name
        flow.active = active
        flow.trigger_type = trigger_type
        flow.time_window = time_window
        flow.member_updated = member

        Workflow.update_string_id(
            session=session,
            flow=flow)

        log['info']['update'] = "Success"

        return log