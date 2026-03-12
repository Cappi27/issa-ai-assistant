function parseBookingTime(text) {
      if (!text) return null;

      const dateRegex = /Date:\s*([^\n]+)/i;
      const timeRegex = /Time:\s*([^\n]+)/i;
      
      let dateStr, timeStr;
      
      const dMatch = text.match(dateRegex);
      const tMatch = text.match(timeRegex);
      
      if (dMatch && tMatch) {
         dateStr = dMatch[1].trim();
         timeStr = tMatch[1].trim();
      }

      const timeParts = timeStr.split(/(?:to|-|–)/i);
      const startStr = timeParts[0].trim();
      const endStr = timeParts[1].trim();

      let cleanDateStr = dateStr.replace(/(\d+)(st|nd|rd|th)/gi, '$1');
      let parsedDate = new Date(cleanDateStr);
      const now = new Date();

      if (isNaN(parsedDate.getTime())) {
          return null; // Simplified for test
      } else {
         if (!cleanDateStr.match(/\d{4}/) && parsedDate.getTime() < Date.now() - 86400000) {
             parsedDate.setFullYear(parsedDate.getFullYear() + 1);
         }
      }

      function parseTime(tStr) {
          const match = tStr.match(/(\d{1,2})(?::(\d{2}))?\s*(am|pm)?/i);
          let h = parseInt(match[1]);
          const m = match[2] ? parseInt(match[2]) : 0;
          const ampm = match[3] ? match[3].toLowerCase() : null;
          
          if (ampm === 'pm' && h < 12) h += 12;
          if (ampm === 'am' && h === 12) h = 0;
          return { hours: h, minutes: m };
      }

      const sTime = parseTime(startStr);
      const eTime = parseTime(endStr);

      const startDate = new Date(parsedDate);
      startDate.setHours(sTime.hours, sTime.minutes, 0, 0);

      const endDate = new Date(parsedDate);
      endDate.setHours(eTime.hours, eTime.minutes, 0, 0);

      function formatUTC(d) {
        const yyyy = d.getUTCFullYear();
        const mm = String(d.getUTCMonth() + 1).padStart(2, "0");
        const dd = String(d.getUTCDate()).padStart(2, "0");
        const hh = String(d.getUTCHours()).padStart(2, "0");
        return `${yyyy}${mm}${dd}T${hh}0000Z`; 
      }

      return { start: formatUTC(startDate), end: formatUTC(endDate) };
}

console.log(parseBookingTime("Date: 8th July\nTime: 4 PM - 8 PM"));
