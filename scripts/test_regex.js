const text = `That sounds great! I'll set up your consultation for that time.

Consultation Slot
- *Date:** 13th March
- *Time:** 4 PM - 6 PM
- *Meeting Type:** Onsite

Looking forward to meeting you!`;

const cleanText = text.replace(/[*#•-]/g, "");

const dateMatch = cleanText.match(/Date:\s*(.+)/i);
const timeMatch = cleanText.match(/Time:\s*(.+)/i);
const typeMatch = cleanText.match(/Meeting Type:\s*(.+)/i);

console.log(dateMatch[1].trim());
console.log(timeMatch[1].trim());
console.log(typeMatch[1].trim());

const blockRegex = /(?:[-*#•\s]*Consultation Slot[\s\S]*?Meeting Type[^\n]*\n?)/i;
console.log(text.replace(blockRegex, "\n__CARD_PLACEHOLDER__\n"));
