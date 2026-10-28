import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Button, Card } from "../../components/ui";
import { BrandLogo } from "../../components/BrandLogo";

export function NotFound() {
  return (
    <Frame title="Page not found" message="That address is not part of Elqovanta EV." />
  );
}

export function AccessDenied() {
  return (
    <Frame title="You do not have access" message="This page belongs to a different account role. Driver and station manager tools are kept separate." />
  );
}

export function Unavailable() {
  return (
    <Frame title="The service is unavailable" message="The website could not reach the Elqovanta EV API. Start the backend, then refresh this page." />
  );
}

export function SessionExpired() {
  return (
    <Frame
      title="Your sign-in has ended"
      message="The session expired or was revoked, for example after a password change on another sign-in. Sign in again to continue."
      action={<Link to="/sign-in"><Button>Sign in</Button></Link>}
    />
  );
}

function Frame({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  return (
    <div className="min-h-screen bg-canvas px-4 py-16">
      <Card className="mx-auto max-w-lg">
        <Link className="inline-block max-w-full" to="/" aria-label="Elqovanta EV home"><BrandLogo /></Link>
        <h1 className="mt-2 text-2xl font-semibold text-navy">{title}</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">{message}</p>
        <div className="mt-5 flex gap-2">
          {action ?? <Link to="/"><Button variant="secondary">Back to the start</Button></Link>}
        </div>
      </Card>
    </div>
  );
}
