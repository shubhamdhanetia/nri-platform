import LoginButton from "../../components/LoginButton";
import Link from "next/link";

export default function LoginPage() {
  return (
    <main className="login-page">
      <section className="login-card">
        <Link className="brand" href="/login" aria-label="NRI Platform home">
          <span className="brand-mark">N</span>
          <span>NRI Platform</span>
        </Link>
        <div className="login-copy">
          <p className="eyebrow">A community that feels closer</p>
          <h1>Your people.<br />Your place.</h1>
          <p className="muted">
            Connect with the NRI community, discover local recommendations, and
            share what matters.
          </p>
        </div>
        <div className="login-action">
          <LoginButton />
          <p className="fine-print">Sign in securely with your Google account.</p>
        </div>
        <p className="login-footer">Built for community, wherever home is.</p>
      </section>
      <aside className="login-art" aria-label="Community welcome">
        <div className="art-orbit orbit-one" />
        <div className="art-orbit orbit-two" />
        <div className="art-note">
          <span className="note-icon">✦</span>
          <div>
            <strong>Closer, together.</strong>
            <span>Find your community here.</span>
          </div>
        </div>
        <div className="art-caption">
          <span className="art-dot" />
          A little closer to home
        </div>
      </aside>
    </main>
  );
}
