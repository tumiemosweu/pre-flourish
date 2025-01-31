from django.core.exceptions import ObjectDoesNotExist
from django.apps import apps as django_apps
from edc_action_item.site_action_items import site_action_items
from edc_base.view_mixins import EdcBaseViewMixin
from edc_dashboard.views import DashboardView as BaseDashboardView
from edc_data_manager.models import DataActionItem
from edc_navbar import NavbarViewMixin
from edc_subject_dashboard.view_mixins import SubjectDashboardViewMixin

from ....action_items import PRE_FLOURISH_CAREGIVER_LOCATOR_ACTION
from ....model_wrappers import (
    AppointmentModelWrapper, PreFlourishSubjectConsentModelWrapper)
from ....model_wrappers import (MaternalVisitModelWrapper,
                                PreflourishCaregiverLocatorModelWrapper,
                                PreFlourishDataActionItemModelWrapper)
from ....models import PreFlourishCaregiverLocator


class DashboardView(EdcBaseViewMixin, SubjectDashboardViewMixin,
                    NavbarViewMixin, BaseDashboardView):
    dashboard_url = 'pre_flourish_subject_dashboard_url'
    dashboard_template = 'pre_flourish_subject_dashboard_template'
    appointment_model = 'edc_appointment.appointment'
    appointment_model_wrapper_cls = AppointmentModelWrapper
    consent_model = 'pre_flourish.preflourishconsent'
    consent_model_wrapper_cls = PreFlourishSubjectConsentModelWrapper
    screening_model = 'pre_flourish.preflourishsubjectscreening'
    navbar_name = 'pre_flourish_dashboard'
    navbar_selected_item = 'pre_flourish_consent'
    subject_locator_model = 'flourish_caregiver.caregiverlocator'
    subject_locator_model_wrapper_cls = PreflourishCaregiverLocatorModelWrapper
    visit_model_wrapper_cls = MaternalVisitModelWrapper
    special_forms_include_value = 'pre_flourish/caregiver/dashboard/special_forms.html'

    @property
    def appointments(self):
        """Returns a Queryset of all appointments for this subject.
        """
        if not self._appointments:
            self._appointments = self.appointment_model_cls.objects.filter(
                subject_identifier=self.subject_identifier).order_by(
                'visit_code')
        return self._appointments
    
    @property
    def consent_model_cls(self):
        return django_apps.get_model(self.consent_model)

    @property
    def screening_model_cls(self):
        return django_apps.get_model(self.screening_model)

    @property
    def subject_locator_model_cls(self):
        return django_apps.get_model(self.subject_locator_model)
    
    @property
    def subject_consent(self):
        try:
            consent = self.consent_model_cls.objects.get(
                subject_identifier = self.subject_identifier[:16]
            )
        except self.consent_model_cls.DoesNotExist:
            pass
        else:
            return consent

    @property
    def subject_locator(self):
        """Returns a model instance either saved or unsaved.

        If a save instance does not exits, returns a new unsaved instance.
        """
        
        screening_identifier = self.subject_consent.screening_identifier

        subject_locator_obj = None

        try:
            screening_obj = self.screening_model_cls.objects.get(
                screening_identifier=screening_identifier
            )

            subject_locator_objs = self.subject_locator_model_cls.objects.filter(
                study_maternal_identifier=screening_obj.previous_subject_identifier
            )

            if not subject_locator_objs.exists():
                subject_locator_obj = PreFlourishCaregiverLocator.objects.get(
                    subject_identifier=self.consent.subject_identifier
                )

        except ObjectDoesNotExist:
            pass
        else:
            subject_locator_obj = subject_locator_objs.first()

        return subject_locator_obj

    @property
    def data_action_item(self):
        """Returns a wrapped saved or unsaved consent version.
        """
        model_obj = DataActionItem(subject_identifier=self.subject_identifier)
        return PreFlourishDataActionItemModelWrapper(model_obj=model_obj)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        locator_obj = self.get_locator_info()
        context.update(
            locator_obj=locator_obj,
            data_action_item_add_url=self.data_action_item.href,
            subject_consent=self.consent_wrapped,
            schedule_names=[model.schedule_name for model in self.onschedule_models], )
        return context

    def set_current_schedule(self, onschedule_model_obj=None,
                             schedule=None, visit_schedule=None,
                             is_onschedule=True):
        if onschedule_model_obj:
            if is_onschedule:
                self.current_schedule = schedule
                self.current_visit_schedule = visit_schedule
                self.current_onschedule_model = onschedule_model_obj
            self.onschedule_models.append(onschedule_model_obj)
            self.visit_schedules.update(
                {visit_schedule.name: visit_schedule})

    def get_onschedule_model_obj(self, schedule):
        try:
            return schedule.onschedule_model_cls.objects.get(
                subject_identifier=self.subject_identifier,
                schedule_name=schedule.name)
        except ObjectDoesNotExist:
            return None

    def get_locator_info(self):

        subject_identifier = self.kwargs.get('subject_identifier')
        try:
            obj = self.subject_locator_model_cls.objects.get(
                subject_identifier=subject_identifier)
        except ObjectDoesNotExist:
            return None
        return obj

    def get_subject_locator_or_message(self):
        obj = self.get_locator_info()
        subject_identifier = self.kwargs.get('subject_identifier')

        if not obj:
            action_cls = site_action_items.get(
                self.subject_locator_model_cls.action_name)
            action_item_model_cls = action_cls.action_item_model_cls()
            try:
                action_item_model_cls.objects.get(
                    subject_identifier=subject_identifier,
                    action_type__name=PRE_FLOURISH_CAREGIVER_LOCATOR_ACTION)
            except ObjectDoesNotExist:
                action_cls(
                    subject_identifier=subject_identifier)
        return obj

    def action_cls_item_creator(
            self, subject_identifier=None, action_cls=None, action_type=None):
        action_cls = site_action_items.get(
            action_cls.action_name)
        action_item_model_cls = action_cls.action_item_model_cls()
        try:
            action_item_model_cls.objects.get(
                subject_identifier=subject_identifier,
                action_type__name=action_type)
        except ObjectDoesNotExist:
            action_cls(
                subject_identifier=subject_identifier)
