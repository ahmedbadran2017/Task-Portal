// Lightweight i18n: t() maps the English source string to the active locale.
// Keys ARE the English strings, so untranslated text degrades gracefully.
// Arabic flips the document to RTL (flex/grid handle mirroring natively).
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
  "Add a checklist item…": "أضف بند جديد…",
  "SLA breached": "تخطت الـ SLA",
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
};

const locale = ref(localStorage.getItem("th_lang") || "en");
applyDir();

function applyDir() {
  if (typeof document !== "undefined") {
    document.documentElement.dir = locale.value === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = locale.value;
  }
}

export function useI18n() {
  function t(s, ...args) {
    let out = locale.value === "ar" ? AR[s] || s : s;
    args.forEach((a, i) => (out = out.replace(`{${i}}`, a)));
    return out;
  }
  function setLocale(l) {
    locale.value = l;
    localStorage.setItem("th_lang", l);
    applyDir();
  }
  return { t, locale, setLocale };
}
