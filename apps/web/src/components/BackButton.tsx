import { ArrowLeft } from '@phosphor-icons/react';
import { useNavigate } from 'react-router-dom';

type BackButtonProps = {
  fallbackTo?: string;
  label?: string;
};

export function BackButton({ fallbackTo = '/', label = 'Back' }: BackButtonProps) {
  const navigate = useNavigate();

  return (
    <button
      className="inline-flex min-h-10 items-center gap-2 rounded-md border border-[var(--color-line)] bg-white px-3 text-sm text-[var(--color-muted)] transition duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] hover:border-[var(--color-ink)] hover:text-[var(--color-ink)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-ink)] active:scale-[0.98]"
      onClick={() => {
        if (window.history.length > 1) {
          navigate(-1);
          return;
        }
        navigate(fallbackTo);
      }}
      type="button"
    >
      <ArrowLeft size={16} weight="bold" />
      {label}
    </button>
  );
}
