
      import type {
  ChecklistBundle,
  ClassifiedEvent,
  Reminder,
  ToneProfile,
  UserCalendarPreferences,
} from "./calendar_types";

const DEFAULT_SCHEDULES: Record<string, Array<{ offsetMinutes: number; message: string }>> = {
  domestic_flight: [
    { offsetMinutes: 24 * 60, message: "Quick heads-up — your flight is tomorrow. Check in and save the boarding pass." },
    { offsetMinutes: 12 * 60, message: "Pack the basics tonight so morning-you has it easy." },
    { offsetMinutes: 10 * 60, message: "Set your wake-up alarm now so this doesn’t turn chaotic in the morning." },
    { offsetMinutes: 3 * 60, message: "Time to head out soon. Better to be early than airport-stressed." },
    { offsetMinutes: 30, message: "Final check: ID, phone, wallet, charger, luggage." },
  ],
  international_flight: [
    { offsetMinutes: 48 * 60, message: "Double-check passport, visa, and travel docs now instead of later." },
    { offsetMinutes: 24 * 60, message: "Check in for your flight and keep the boarding pass handy." },
    { offsetMinutes: 12 * 60, message: "Tonight’s packing check: passport, chargers, meds, cards, and travel basics." },
    { offsetMinutes: 4 * 60, message: "Time to leave with enough buffer for immigration and check-in." },
  ],
  work_meeting: [
    { offsetMinutes: 60, message: "Quick reminder — skim the agenda and open anything you’ll need." },
    { offsetMinutes: 15, message: "Meeting soon. Link, notes, and charger check." },
  ],
  presentation: [
    { offsetMinutes: 24 * 60, message: "Presentation tomorrow. Do one clean deck review tonight and call it done." },
    { offsetMinutes: 60, message: "Open the final deck now, not five minutes before." },
    { offsetMinutes: 20, message: "Laptop, charger, deck, notes. You’re set." },
  ],
  wedding: [
    { offsetMinutes: 48 * 60, message: "Wedding coming up. Good time to finalize outfit, shoes, bag, and jewellery." },
    { offsetMinutes: 24 * 60, message: "Steam or iron the outfit tonight and keep everything together." },
    { offsetMinutes: 60, message: "Wedding soon. Final check: outfit, shoes, bag, gift, phone, wallet." },
  ],
  doctor_appointment: [
    { offsetMinutes: 12 * 60, message: "Doctor appointment tomorrow. Keep reports, ID, and any notes in one place tonight." },
    { offsetMinutes: 60, message: "Appointment soon. Reports, wallet, phone, and time to head out." },
  ],
  gym_class: [
    { offsetMinutes: 10 * 60, message: "Lay out your workout clothes tonight. Makes tomorrow easier." },
    { offsetMinutes: 45, message: "Workout soon. Shoes, bottle, towel, and you’re good." },
  ],
  electricity_bill: [
    { offsetMinutes: 7 * 24 * 60, message: "Electricity bill is due in 7 days." },
    { offsetMinutes: 3 * 24 * 60, message: "Electricity bill due in 3 days." },
    { offsetMinutes: 24 * 60, message: "Electricity bill is due tomorrow." },
    { offsetMinutes: 0, message: "Today’s the last day to pay the electricity bill." },
  ],
  credit_card_bill: [
    { offsetMinutes: 5 * 24 * 60, message: "Credit card payment is due in 5 days. Nice one to clear before it gets too close." },
    { offsetMinutes: 2 * 24 * 60, message: "Credit card bill due in 2 days." },
    { offsetMinutes: 24 * 60, message: "Credit card bill is due tomorrow." },
    { offsetMinutes: 0, message: "Today’s the due date for your credit card bill." },
  ],
  rent_payment: [
    { offsetMinutes: 5 * 24 * 60, message: "Rent is due in 5 days." },
    { offsetMinutes: 2 * 24 * 60, message: "Rent payment due in 2 days." },
    { offsetMinutes: 24 * 60, message: "Rent is due tomorrow." },
    { offsetMinutes: 0, message: "Today’s the due date for rent." },
  ],
};

function toneForEvent(event: ClassifiedEvent, preferences?: UserCalendarPreferences): ToneProfile {
  if (preferences?.toneProfile) return preferences.toneProfile;
  if (preferences?.prefersShortMessages) return "efficient";
  if (event.group === "health") return "gentle";
  if (event.group === "fitness") return "upbeat";
  if (event.group === "finance" || event.group === "work") return "efficient";
  return "casual_warm";
}

function notificationCap(preferences?: UserCalendarPreferences): number {
  switch (preferences?.preferredReminderDensity) {
    case "light":
      return 2;
    case "high_support":
      return 6;
    default:
      return 4;
  }
}

function toSendAtISO(eventStartISO: string, offsetMinutes: number): string {
  const eventStart = new Date(eventStartISO).getTime();
  const sendAt = eventStart - offsetMinutes * 60 * 1000;
  return new Date(sendAt).toISOString();
}

function checklistSummary(checklist: ChecklistBundle): string[] {
  const lines: string[] = [];
  if (checklist.carry?.items.length) lines.push(`Carry: ${checklist.carry.items.slice(0, 3).join(", ")}`);
  if (checklist.wear?.items.length) lines.push(`Wear: ${checklist.wear.items.slice(0, 3).join(", ")}`);
  if (checklist.payment?.items.length) lines.push(`Payment: ${checklist.payment.items.slice(0, 2).join(", ")}`);
  return lines;
}

export function buildCalendarReminders(
  event: ClassifiedEvent,
  checklist: ChecklistBundle,
  preferences?: UserCalendarPreferences,
): Reminder[] {
  const base = DEFAULT_SCHEDULES[event.subtype] ?? [
    { offsetMinutes: 60, message: `Quick reminder — ${event.title} is coming up soon.` },
  ];

  const cap = notificationCap(preferences);
  const toneProfile = toneForEvent(event, preferences);
  const summary = checklistSummary(checklist);

  let reminders = base.slice(0, cap).map((item, index) => ({
    id: `${event.eventId}_${index}`,
    offsetMinutes: item.offsetMinutes,
    message: item.message,
    priority: event.priority,
    toneProfile,
    sendAtISO: toSendAtISO(event.startAtISO, item.offsetMinutes),
  }));

  if (summary.length > 0 && reminders.length > 0) {
    reminders = reminders.map((reminder, index) =>
      index === reminders.length - 1
        ? { ...reminder, message: `${reminder.message} ${summary[0]}.` }
        : reminder,
    );
  }

  if (event.autoPayEnabled && event.group === "finance") {
    reminders = reminders.map((reminder) =>
      reminder.offsetMinutes <= 24 * 60
        ? {
            ...reminder,
            message:
              reminder.offsetMinutes === 0
                ? "This should auto-pay today. Worth a quick glance later to be sure it went through."
                : "This gets auto-paid soon. Just make sure the account is ready.",
          }
        : reminder,
    );
  }

  return reminders;
}
