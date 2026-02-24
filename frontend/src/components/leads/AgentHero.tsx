import { cn } from "@/lib/utils";

interface AgentHeroProps {
  name: string;
  headline: string | null;
  bio: string | null;
  photoUrl: string | null;
  phone: string | null;
  email: string | null;
  brokerageName: string | null;
  compact?: boolean;
}

export function AgentHero({
  name,
  headline,
  bio,
  photoUrl,
  phone,
  email,
  brokerageName,
  compact = false,
}: AgentHeroProps) {
  return (
    <section
      className={cn(
        "flex flex-col items-center bg-white px-4 text-center",
        compact ? "py-6" : "py-10"
      )}
    >
      {/* Agent photo */}
      <div
        className={cn(
          "mb-4 overflow-hidden rounded-full bg-gray-200",
          compact ? "h-24 w-24" : "h-32 w-32"
        )}
      >
        {photoUrl ? (
          <img
            src={photoUrl}
            alt={name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center text-3xl font-bold text-gray-400">
            {name
              .split(" ")
              .map((n) => n[0])
              .join("")
              .slice(0, 2)
              .toUpperCase()}
          </div>
        )}
      </div>

      {/* Name and headline */}
      <h1
        className={cn(
          "font-bold text-primary",
          compact ? "text-xl" : "text-2xl md:text-3xl"
        )}
      >
        {name}
      </h1>

      {headline && (
        <p
          className={cn(
            "mt-1 text-gray-500",
            compact ? "text-sm" : "text-base md:text-lg"
          )}
        >
          {headline}
        </p>
      )}

      {brokerageName && (
        <p className="mt-1 text-xs font-medium tracking-wide text-accent uppercase">
          {brokerageName}
        </p>
      )}

      {/* Bio */}
      {bio && !compact && (
        <p className="mx-auto mt-4 max-w-lg text-sm leading-relaxed text-gray-600">
          {bio}
        </p>
      )}

      {/* Contact links */}
      {(phone || email) && (
        <div className="mt-4 flex flex-wrap items-center justify-center gap-4">
          {phone && (
            <a
              href={`tel:${phone}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-primary hover:text-white"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path
                  fillRule="evenodd"
                  d="M2 3.5A1.5 1.5 0 0 1 3.5 2h1.148a1.5 1.5 0 0 1 1.465 1.175l.716 3.223a1.5 1.5 0 0 1-1.052 1.767l-.933.267c-.41.117-.643.555-.48.95a11.542 11.542 0 0 0 6.254 6.254c.395.163.833-.07.95-.48l.267-.933a1.5 1.5 0 0 1 1.767-1.052l3.223.716A1.5 1.5 0 0 1 18 15.352V16.5a1.5 1.5 0 0 1-1.5 1.5H15c-1.149 0-2.263-.15-3.326-.43A13.022 13.022 0 0 1 2.43 8.326 13.019 13.019 0 0 1 2 5V3.5Z"
                  clipRule="evenodd"
                />
              </svg>
              {phone}
            </a>
          )}
          {email && (
            <a
              href={`mailto:${email}`}
              className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 px-4 py-2 text-sm font-medium text-primary transition-colors hover:bg-primary hover:text-white"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
                className="h-4 w-4"
              >
                <path d="M3 4a2 2 0 0 0-2 2v1.161l8.441 4.221a1.25 1.25 0 0 0 1.118 0L19 7.162V6a2 2 0 0 0-2-2H3Z" />
                <path d="m19 8.839-7.77 3.885a2.75 2.75 0 0 1-2.46 0L1 8.839V14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V8.839Z" />
              </svg>
              Email
            </a>
          )}
        </div>
      )}
    </section>
  );
}
