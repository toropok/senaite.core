Duplicate Analysis verification guard and event
-----------------------------------------------

Running this test from the buildout directory:

    bin/test test_textual_doctests -t WorkflowDuplicateAnalysisVerify


Test Setup
..........

Needed Imports:

    >>> from AccessControl.PermissionRole import rolesForPermissionOn
    >>> from bika.lims import api
    >>> from bika.lims.interfaces import IVerified
    >>> from bika.lims.utils.analysisrequest import create_analysisrequest
    >>> from bika.lims.workflow import doActionFor as do_action_for
    >>> from bika.lims.workflow import isTransitionAllowed
    >>> from DateTime import DateTime
    >>> from plone.app.testing import setRoles
    >>> from plone.app.testing import TEST_USER_ID
    >>> from plone.app.testing import TEST_USER_PASSWORD

Functional Helpers:

    >>> def start_server():
    ...     from Testing.ZopeTestCase.utils import startZServer
    ...     ip, port = startZServer()
    ...     return "http://{}:{}/{}".format(ip, port, portal.id)

    >>> def timestamp(format="%Y-%m-%d"):
    ...     return DateTime().strftime(format)

    >>> def start_server():
    ...     from Testing.ZopeTestCase.utils import startZServer
    ...     ip, port = startZServer()
    ...     return "http://{}:{}/{}".format(ip, port, portal.id)

    >>> def new_ar(services):
    ...     values = {
    ...         'Client': client.UID(),
    ...         'Contact': contact.UID(),
    ...         'DateSampled': date_now,
    ...         'SampleType': sampletype.UID()}
    ...     service_uids = map(api.get_uid, services)
    ...     ar = create_analysisrequest(client, request, values, service_uids)
    ...     transitioned = do_action_for(ar, "receive")
    ...     return ar

    >>> def to_new_worksheet_with_duplicate(ar):
    ...     worksheet = api.create(portal.worksheets, "Worksheet")
    ...     for analysis in ar.getAnalyses(full_objects=True):
    ...         worksheet.addAnalysis(analysis)
    ...     worksheet.addDuplicateAnalyses(1)
    ...     return worksheet

    >>> def submit_regular_analyses(worksheet):
    ...     for analysis in worksheet.getRegularAnalyses():
    ...         analysis.setResult(13)
    ...         do_action_for(analysis, "submit")

    >>> def try_transition(object, transition_id, target_state_id):
    ...      success = do_action_for(object, transition_id)[0]
    ...      state = api.get_workflow_status_of(object)
    ...      return success and state == target_state_id

    >>> def get_roles_for_permission(permission, context):
    ...     allowed = set(rolesForPermissionOn(permission, context))
    ...     return sorted(allowed)

Variables:

    >>> portal = self.portal
    >>> request = self.request
    >>> setup = portal.setup
    >>> bikasetup = portal.bika_setup
    >>> date_now = DateTime().strftime("%Y-%m-%d")
    >>> date_future = (DateTime() + 5).strftime("%Y-%m-%d")

We need to create some basic objects for the test:

    >>> setRoles(portal, TEST_USER_ID, ['LabManager',])
    >>> client = api.create(portal.clients, "Client", Name="Happy Hills", ClientID="HH", MemberDiscountApplies=True)
    >>> contact = api.create(client, "Contact", Firstname="Rita", Lastname="Mohale")
    >>> sampletype = api.create(setup.sampletypes, "SampleType", title="Water", Prefix="W")
    >>> labcontact = api.create(bikasetup.bika_labcontacts, "LabContact", Firstname="Lab", Lastname="Manager")
    >>> department = api.create(setup.departments, "Department", title="Chemistry", Manager=labcontact)
    >>> category = api.create(setup.analysiscategories, "AnalysisCategory", title="Metals", Department=department)
    >>> Cu = api.create(bikasetup.bika_analysisservices, "AnalysisService", title="Copper", Keyword="Cu", Price="15", Category=category.UID(), Accredited=True)
    >>> Fe = api.create(bikasetup.bika_analysisservices, "AnalysisService", title="Iron", Keyword="Fe", Price="10", Category=category.UID())
    >>> Au = api.create(bikasetup.bika_analysisservices, "AnalysisService", title="Gold", Keyword="Au", Price="20", Category=category.UID())


Duplicate verification basic constraints
........................................

Create a Worksheet and submit regular analyses:

    >>> ar = new_ar([Cu])
    >>> worksheet = to_new_worksheet_with_duplicate(ar)
    >>> submit_regular_analyses(worksheet)

Get the duplicate and submit:

    >>> duplicate = worksheet.getDuplicateAnalyses()[0]
    >>> duplicate.setResult(12)
    >>> try_transition(duplicate, "submit", "to_be_verified")
    True
    >>> api.get_workflow_status_of(duplicate)
    'to_be_verified'

I cannot verify the duplicate because I am the same user who submitted:

    >>> try_transition(duplicate, "verify", "verified")
    False
    >>> api.get_workflow_status_of(duplicate)
    'to_be_verified'

And I cannot verify the Worksheet, because it can only be verified once all
analyses it contains are verified (and this is done automatically):

    >>> try_transition(worksheet, "verify", "verified")
    False
    >>> api.get_workflow_status_of(worksheet)
    'to_be_verified'

But if I enable self-verification:

    >>> bikasetup.setSelfVerificationEnabled(True)
    >>> bikasetup.getSelfVerificationEnabled()
    True

Then, I can verify my own result:

    >>> try_transition(duplicate, "verify", "verified")
    True

And the worksheet transitions to `verified`:

    >>> api.get_workflow_status_of(worksheet)
    'to_be_verified'

And we cannot re-verify a duplicate that has been verified already:

    >>> try_transition(duplicate, "verify", "verified")
    False

To ensure consistency amongst tests, we disable self-verification:

    >>> bikasetup.setSelfVerificationEnabled(False)
    >>> bikasetup.getSelfVerificationEnabled()
    False


Check permissions for Verify transition
.......................................

Enable self verification of results:

    >>> bikasetup.setSelfVerificationEnabled(True)
    >>> bikasetup.getSelfVerificationEnabled()
    True

Create a Worksheet and submit regular analyses:

    >>> ar = new_ar([Cu])
    >>> worksheet = to_new_worksheet_with_duplicate(ar)
    >>> submit_regular_analyses(worksheet)

Get the duplicate and submit:

    >>> duplicate = worksheet.getDuplicateAnalyses()[0]
    >>> duplicate.setResult(12)
    >>> try_transition(duplicate, "submit", "to_be_verified")
    True

Exactly these roles can verify:

    >>> get_roles_for_permission("senaite.core: Transition: Verify", duplicate)
    ['LabManager', 'Manager', 'Verifier']

Current user can verify because has the `LabManager` role:

    >>> isTransitionAllowed(duplicate, "verify")
    True

Also if the user has the roles `Manager` or `Verifier`:

    >>> setRoles(portal, TEST_USER_ID, ['Manager',])
    >>> isTransitionAllowed(duplicate, "verify")
    True

TODO Workflow Verifier should be able to verify a duplicate!
The code below throws an
`Unauthorized: Not authorized to access binding: context` error, rised by
https://github.com/MatthewWilkes/Zope/blob/master/src/Shared/DC/Scripts/Bindings.py#L198

#    >>> setRoles(portal, TEST_USER_ID, ['Verifier',])
#    >>> isTransitionAllowed(duplicate, "verify")
#    True

But cannot for other roles:

    >>> setRoles(portal, TEST_USER_ID, ['Analyst', 'Authenticated', 'LabClerk'])
    >>> isTransitionAllowed(duplicate, "verify")
    False

Even if is `Owner`

    >>> setRoles(portal, TEST_USER_ID, ['Owner'])
    >>> isTransitionAllowed(duplicate, "verify")
    False

And Clients cannot neither:

    >>> setRoles(portal, TEST_USER_ID, ['Client'])
    >>> isTransitionAllowed(duplicate, "verify")
    False

Reset the roles for current user:

    >>> setRoles(portal, TEST_USER_ID, ['LabManager',])

And to ensure consistency amongst tests, we disable self-verification:

    >>> bikasetup.setSelfVerificationEnabled(False)
    >>> bikasetup.getSelfVerificationEnabled()
    False


IVerified interface is provided by duplicate analysis that are verified
.......................................................................

When verified, duplicate analyses are marked with the `IVerified` interface:

    >>> bikasetup.setSelfVerificationEnabled(True)
    >>> sample = new_ar([Cu])
    >>> worksheet = to_new_worksheet_with_duplicate(sample)
    >>> duplicate = worksheet.getDuplicateAnalyses()[0]
    >>> duplicate.setResult(12)
    >>> success = do_action_for(duplicate, "submit")
    >>> IVerified.providedBy(duplicate)
    False

    >>> success = do_action_for(duplicate, "verify")
    >>> IVerified.providedBy(duplicate)
    True

    >>> bikasetup.setSelfVerificationEnabled(False)
