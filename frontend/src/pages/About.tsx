export default function About() {
  return (
    <div>
      <div className="page-head">
        <h1>About With Us</h1>
        <p className="muted">A recovery plan for the new mother that the whole household carries.</p>
      </div>
      <div className="grid-thirds">
      <section className="card stack-sm">
        <h2>Three rules we never break</h2>
        <p><strong>The mother gets her space.</strong> Her rest windows are never touched, and we plan her for half of what she states.</p>
        <p><strong>The maths is never left to AI.</strong> Who does what, and how fair it is, comes from plain, tested code. People set their own capacity and limits.</p>
        <p><strong>Your reasons never leave you.</strong> Reasons, assistant instructions, requests, answers and chats are visible only to you. The household sees only the published plan.</p>
      </section>
      <section className="card stack-sm">
        <h2>Where AI helps</h2>
        <p>Gemini reads the discharge sheet, fills your form from your own words, answers questions about your own week, and writes one kind line when you ask it to. A person confirms everything, and every AI feature has a plain fallback.</p>
      </section>
      <section className="card card-warn stack-sm">
        <h2>Not a medical device</h2>
        <p className="warn-ink">With Us only repeats what the doctor wrote. It never gives medical advice, doses or diagnosis. Ask your doctor about anything unclear.</p>
      </section>
      </div>
    </div>
  );
}
