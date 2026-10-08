const LABELS: Record<string, string> = {
  home: 'Home tutor',
  online: 'Online tutor',
  english: 'English',
  hindi: 'Hindi',
  male: 'Male',
  female: 'Female',
}

export function displayValue(value: string) {
  const text = value.trim()
  return LABELS[text.toLowerCase()] || text
}
