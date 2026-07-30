// Lightweight i18n: t() maps the English source string to the active locale.
// Keys ARE the English strings, so untranslated text degrades gracefully.
// Arabic flips the document to RTL (flex/grid handle mirroring natively).
// Default locale = the user's ERPNext language (window.user_lang, injected by
// the Jinja shell); an explicit in-app choice (localStorage) wins over it.
import { ref } from "vue";

const AR = {
  // navigation & chrome
  "Dashboard": "الرئيسية",
  "Board": "اللوحة",
  "All Tickets": "كل التذاكر",
  "Tickets": "التذاكر",
  "Teams": "الفرق",
  "Settings": "الإعدادات",
  "My Work": "شغلي",
  "Task Hub": "مركز المهام",
  "New Ticket": "تذكرة جديدة",
  "New": "جديدة",
  "Notifications": "الإشعارات",
  "Mark all read": "تعليم الكل كمقروء",
  "Nothing yet — you're all caught up 🎉": "مفيش جديد — انت متابع كل حاجة 🎉",

  // statuses
  "Open": "مفتوحة",
  "In Progress": "قيد التنفيذ",
  "In Review": "قيد المراجعة",
  "Resolved": "محلولة",
  "Closed": "مغلقة",
  "Cancelled": "ملغاة",

  // priorities & types
  "Urgent": "عاجلة",
  "High": "عالية",
  "Medium": "متوسطة",
  "Low": "منخفضة",
  "Task": "مهمة",
  "Problem": "مشكلة",
  "Request": "طلب",

  // dashboard
  "tickets in progress": "تذاكر جارية",
  "SLA Breached": "تخطت الـ SLA",
  "past deadline": "تعدّت الموعد",
  "My Queue": "طابوري",
  "assigned to me": "معينة عليّا",
  "Unassigned": "بدون مسؤول",
  "need an owner": "محتاجة مسؤول",
  "Open work by portal": "الشغل المفتوح حسب البوابة",
  "Open by priority": "المفتوح حسب الأولوية",
  "Everything, by status": "الكل حسب الحالة",
  "Created vs resolved — last 8 weeks": "الجديد مقابل المحلول — آخر ٨ أسابيع",
  "Portal health (30 days)": "صحة البوابات (٣٠ يوم)",
  "No open tickets — all clear": "مفيش تذاكر مفتوحة — تمام",
  "Created": "جديدة",
  "Avg resolution": "متوسط الحل",

  // board & list
  "All portals": "كل البوابات",
  "Any priority": "أي أولوية",
  "Any status": "أي حالة",
  "Any type": "أي نوع",
  "My tickets": "تذاكري",
  "SLA breached": "تخطت الـ SLA",
  "Refresh": "تحديث",
  "Nothing here": "مفيش حاجة هنا",
  "Loading tickets…": "جاري تحميل التذاكر…",
  "No tickets match.": "مفيش تذاكر مطابقة.",
  "Search title or ID…": "ابحث بالعنوان أو الرقم…",
  "Mine": "بتاعتي",
  "tickets": "تذكرة",
  "Ticket": "التذكرة",
  "Portal": "البوابة",
  "Priority": "الأولوية",
  "Status": "الحالة",
  "Assignee": "المسؤول",
  "Updated": "آخر تحديث",
  "Breached": "متأخرة",
  "Export CSV": "تصدير CSV",
  "Prev": "السابق",
  "Next": "التالي",
  "of": "من",
  "Department": "القسم",
  "Showing first {0} of {1} tickets — refine the filters.":
    "معروض أول {0} من {1} تذكرة — ضيّق الفلاتر.",

  // ticket card / drawer
  "Title": "العنوان",
  "Type": "النوع",
  "Due Date": "تاريخ الاستحقاق",
  "Due": "الاستحقاق",
  "Assign To": "تعيين إلى",
  "Assigned To": "المسؤول",
  "Description": "الوصف",
  "Attachments": "المرفقات",
  "Add files": "إضافة ملفات",
  "Add": "إضافة",
  "Comments": "التعليقات",
  "Activity": "السجل",
  "Checklist": "قائمة المهام",
  "Watch": "متابعة",
  "Watching": "بتتابعها",
  "Edit": "تعديل",
  "Save": "حفظ",
  "Cancel": "إلغاء",
  "Send": "إرسال",
  "Create Ticket": "إنشاء التذكرة",
  "Creating…": "جاري الإنشاء…",
  "Saving…": "جاري الحفظ…",
  "Source Portal": "بوابة المصدر",
  "Linked Record": "السجل المرتبط",
  "Reported by": "أبلغ عنها",
  "SLA deadline": "موعد الـ SLA",
  "No attachments.": "مفيش مرفقات.",
  "No comments yet.": "مفيش تعليقات لسه.",
  "Write a comment… type @ to mention": "اكتب تعليق… اكتب @ لعمل mention",

  // AI assist
  "Rewrite in English": "إعادة صياغة بالإنجليزية",
  "Rewriting…": "جاري إعادة الصياغة…",
  "AI suggestion": "اقتراح الذكاء الاصطناعي",
  "Use suggestion": "استخدم الاقتراح",
  "Keep original": "خليني على نصي",
  "AI rewrite failed": "فشلت إعادة الصياغة",
  "Add a checklist item…": "أضف بند جديد…",
  "— Unassigned —": "— بدون مسؤول —",
  "Search by name…": "ابحث بالاسم…",
  "No one matches.": "مفيش حد مطابق.",
  "Short summary of the task or problem": "ملخص قصير للمهمة أو المشكلة",
  "Add context, steps, links…": "أضف تفاصيل، خطوات، لينكات…",

  // teams
  "Performance per department — resolution speed and SLA discipline, last":
    "الأداء حسب القسم — سرعة الحل والالتزام بالـ SLA، آخر",
  "days.": "يوم.",
  "people": "أفراد",
  "person": "فرد",
  "Resolved (30d)": "المحلول (٣٠ يوم)",
  "Avg fix": "متوسط الحل",
  "SLA on-time": "الالتزام بالـ SLA",
  "View team tickets →": "تذاكر الفريق ←",
  "no data": "مفيش بيانات",
  "No department activity yet.": "مفيش نشاط أقسام لسه.",

  // settings
  "SLA budgets": "ميزانيات الـ SLA",
  "Defaults & behaviour": "الافتراضيات والسلوك",
  "Auto-tickets": "التذاكر التلقائية",
  "Recurring tickets": "التذاكر المتكررة",
  "Language": "اللغة",
  "Save Settings": "حفظ الإعدادات",
  "Reset": "إعادة ضبط",
  "Default type": "النوع الافتراضي",
  "Default priority": "الأولوية الافتراضية",
  "Who can be assigned tickets": "مين ينفع يتعين عليه تذاكر",
  "Daily": "يومي",
  "Weekly": "أسبوعي",
  "Monthly": "شهري",
  "Active": "مفعّلة",
  "Add rule": "إضافة قاعدة",
  "Delete": "حذف",
  "hours": "ساعة",
  "All workspaces": "كل المساحات",
  "Workspace": "مساحة العمل",
  "Workspaces": "مساحات العمل",
  "open": "مفتوحة",
  "Stage": "المرحلة",
  "Add workspace": "إضافة مساحة",
  "Stages (board columns)": "المراحل (أعمدة اللوحة)",
  "Counts as": "تُحسب كـ",
  "SLA applies": "الـ SLA مفعّل",
  "Members from department": "الأعضاء من قسم",
  "Calendar": "التقويم",
  "Today": "اليوم",
  "No tickets with a due date this month.": "مفيش تذاكر بتاريخ استحقاق الشهر ده.",
  "Template": "قالب",
  "Templates": "القوالب",
  "No template": "بدون قالب",
  "Add template": "إضافة قالب",
  "Departments": "الأقسام",
  "Person": "الشخص",
  "Open now": "مفتوح دلوقتي",
  "Reported": "أبلغ عن",
  "Loading…": "جاري التحميل…",
  "Loading scorecards…": "جاري تحميل الأداء…",
};

const FR = {
  // navigation & chrome
  "Dashboard": "Tableau de bord",
  "Board": "Kanban",
  "All Tickets": "Tous les tickets",
  "Tickets": "Tickets",
  "Teams": "Équipes",
  "Settings": "Paramètres",
  "My Work": "Mon travail",
  "Task Hub": "Centre des tâches",
  "New Ticket": "Nouveau ticket",
  "New": "Nouveau",
  "Notifications": "Notifications",
  "Mark all read": "Tout marquer comme lu",
  "Nothing yet — you're all caught up 🎉": "Rien de nouveau — vous êtes à jour 🎉",

  // statuses
  "Open": "Ouvert",
  "In Progress": "En cours",
  "In Review": "En revue",
  "Resolved": "Résolu",
  "Closed": "Fermé",
  "Cancelled": "Annulé",

  // priorities & types
  "Urgent": "Urgent",
  "High": "Haute",
  "Medium": "Moyenne",
  "Low": "Basse",
  "Task": "Tâche",
  "Problem": "Problème",
  "Request": "Demande",

  // dashboard
  "tickets in progress": "tickets en cours",
  "SLA Breached": "SLA dépassé",
  "past deadline": "délai dépassé",
  "My Queue": "Ma file",
  "assigned to me": "qui me sont assignés",
  "Unassigned": "Non assignés",
  "need an owner": "sans responsable",
  "Open work by portal": "Travail ouvert par portail",
  "Open by priority": "Ouverts par priorité",
  "Everything, by status": "Tout, par statut",
  "Created vs resolved — last 8 weeks": "Créés vs résolus — 8 dernières semaines",
  "Portal health (30 days)": "Santé des portails (30 jours)",
  "No open tickets — all clear": "Aucun ticket ouvert — tout est en ordre",
  "Created": "Créés",
  "Avg resolution": "Résolution moy.",

  // board & list
  "All portals": "Tous les portails",
  "Any priority": "Toute priorité",
  "Any status": "Tout statut",
  "Any type": "Tout type",
  "My tickets": "Mes tickets",
  "SLA breached": "SLA dépassé",
  "Refresh": "Actualiser",
  "Nothing here": "Rien ici",
  "Loading tickets…": "Chargement des tickets…",
  "No tickets match.": "Aucun ticket ne correspond.",
  "Search title or ID…": "Rechercher par titre ou ID…",
  "Mine": "À moi",
  "tickets": "tickets",
  "Ticket": "Ticket",
  "Portal": "Portail",
  "Priority": "Priorité",
  "Status": "Statut",
  "Assignee": "Responsable",
  "Updated": "Mis à jour",
  "Breached": "Dépassé",
  "Export CSV": "Exporter CSV",
  "Prev": "Préc.",
  "Next": "Suiv.",
  "of": "sur",
  "Department": "Département",
  "Showing first {0} of {1} tickets — refine the filters.":
    "Affichage des {0} premiers sur {1} tickets — affinez les filtres.",

  // ticket card / drawer
  "Title": "Titre",
  "Type": "Type",
  "Due Date": "Échéance",
  "Due": "Échéance",
  "Assign To": "Assigner à",
  "Assigned To": "Responsable",
  "Description": "Description",
  "Attachments": "Pièces jointes",
  "Add files": "Ajouter des fichiers",
  "Add": "Ajouter",
  "Comments": "Commentaires",
  "Activity": "Activité",
  "Checklist": "Checklist",
  "Watch": "Suivre",
  "Watching": "Suivi",
  "Edit": "Modifier",
  "Save": "Enregistrer",
  "Cancel": "Annuler",
  "Send": "Envoyer",
  "Create Ticket": "Créer le ticket",
  "Creating…": "Création…",
  "Saving…": "Enregistrement…",
  "Source Portal": "Portail source",
  "Linked Record": "Enregistrement lié",
  "Reported by": "Signalé par",
  "SLA deadline": "Échéance SLA",
  "No attachments.": "Aucune pièce jointe.",
  "No comments yet.": "Aucun commentaire pour l'instant.",
  "Write a comment… type @ to mention": "Écrire un commentaire… tapez @ pour mentionner",

  // AI assist
  "Rewrite in English": "Reformuler en anglais",
  "Rewriting…": "Reformulation…",
  "AI suggestion": "Suggestion IA",
  "Use suggestion": "Utiliser la suggestion",
  "Keep original": "Garder l'original",
  "AI rewrite failed": "Échec de la reformulation",
  "Add a checklist item…": "Ajouter un élément…",
  "— Unassigned —": "— Non assigné —",
  "Search by name…": "Rechercher par nom…",
  "No one matches.": "Aucun résultat.",
  "Short summary of the task or problem": "Résumé court de la tâche ou du problème",
  "Add context, steps, links…": "Ajoutez contexte, étapes, liens…",

  // teams
  "Performance per department — resolution speed and SLA discipline, last":
    "Performance par département — vitesse de résolution et respect du SLA, derniers",
  "days.": "jours.",
  "people": "personnes",
  "person": "personne",
  "Resolved (30d)": "Résolus (30 j)",
  "Avg fix": "Résolution moy.",
  "SLA on-time": "SLA à temps",
  "View team tickets →": "Voir les tickets de l'équipe →",
  "no data": "aucune donnée",
  "No department activity yet.": "Aucune activité de département pour l'instant.",

  // settings
  "SLA budgets": "Budgets SLA",
  "Defaults & behaviour": "Valeurs par défaut et comportement",
  "Auto-tickets": "Tickets automatiques",
  "Recurring tickets": "Tickets récurrents",
  "Language": "Langue",
  "Save Settings": "Enregistrer les paramètres",
  "Reset": "Réinitialiser",
  "Default type": "Type par défaut",
  "Default priority": "Priorité par défaut",
  "Who can be assigned tickets": "Qui peut être assigné aux tickets",
  "Daily": "Quotidien",
  "Weekly": "Hebdomadaire",
  "Monthly": "Mensuel",
  "Active": "Actif",
  "Add rule": "Ajouter une règle",
  "Delete": "Supprimer",
  "hours": "heures",
  "All workspaces": "Tous les espaces",
  "Workspace": "Espace de travail",
  "Workspaces": "Espaces de travail",
  "open": "ouverts",
  "Stage": "Étape",
  "Add workspace": "Ajouter un espace",
  "Stages (board columns)": "Étapes (colonnes du kanban)",
  "Counts as": "Compte comme",
  "SLA applies": "SLA actif",
  "Members from department": "Membres du département",
  "Calendar": "Calendrier",
  "Today": "Aujourd'hui",
  "No tickets with a due date this month.": "Aucun ticket avec une échéance ce mois-ci.",
  "Template": "Modèle",
  "Templates": "Modèles",
  "No template": "Sans modèle",
  "Add template": "Ajouter un modèle",
  "Departments": "Départements",
  "Person": "Personne",
  "Open now": "Ouverts actuellement",
  "Reported": "Signalés",
  "Loading…": "Chargement…",
  "Loading scorecards…": "Chargement des indicateurs…",
};

const DICTS = { ar: AR, fr: FR };

// Shown in the header toggle + Settings, in display order.
export const LOCALES = [
  { code: "en", label: "EN", name: "English" },
  { code: "ar", label: "ع", name: "العربية" },
  { code: "fr", label: "FR", name: "Français" },
];

const KNOWN = ["en", "ar", "fr"];

function normalize(l) {
  l = String(l || "").toLowerCase().slice(0, 2);
  return KNOWN.includes(l) ? l : "en";
}

function initialLocale() {
  const saved = localStorage.getItem("th_lang");
  if (saved && KNOWN.includes(saved)) return saved;
  // No explicit choice yet — follow the user's ERPNext language.
  return normalize(typeof window !== "undefined" ? window.user_lang : "");
}

const locale = ref(initialLocale());
applyDir();

function applyDir() {
  if (typeof document !== "undefined") {
    document.documentElement.dir = locale.value === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = locale.value;
  }
}

export function useI18n() {
  function t(s, ...args) {
    const dict = DICTS[locale.value];
    let out = (dict && dict[s]) || s;
    args.forEach((a, i) => (out = out.replace(`{${i}}`, a)));
    return out;
  }
  function setLocale(l) {
    locale.value = l;
    localStorage.setItem("th_lang", l);
    applyDir();
  }
  return { t, locale, setLocale, LOCALES };
}
