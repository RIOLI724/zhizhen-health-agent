interface FollowUpChipsProps {
  chips: string[];
  onSelect: (chip: string) => void;
}

export function FollowUpChips({ chips, onSelect }: FollowUpChipsProps) {
  if (chips.length === 0) return null;

  return (
    <div className="chips">
      {chips.map((chip) => (
        <button
          className="chip"
          type="button"
          key={chip}
          onClick={() => onSelect(chip)}
        >
          {chip}
        </button>
      ))}
    </div>
  );
}
