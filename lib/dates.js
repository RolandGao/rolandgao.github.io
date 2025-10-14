const pacificFormatter = new Intl.DateTimeFormat('en-US', {
  timeZone: 'America/Los_Angeles',
  year: 'numeric',
  month: 'long',
  day: 'numeric',
});

export const formatPacificDate = dateString => {
  if (!dateString) {
    return '';
  }

  const [year, month, day] = dateString.split('-').map(Number);
  if (![year, month, day].every(Number.isFinite)) {
    return dateString;
  }

  const utcMidday = new Date(Date.UTC(year, month - 1, day, 12));
  return pacificFormatter.format(utcMidday);
};
