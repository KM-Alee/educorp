# Page Specs: Public And Shared

## How To Read These Specs

Each page spec defines:

- page purpose
- primary users
- route recommendation
- key modules
- main actions
- important states

## Public Home

### Status

Proposed.

### Route

`/`

### Purpose

Give first-time visitors a clean entry into the product without turning EduCorp into a marketing-heavy site.

### Key modules

- product summary
- `Explore courses` CTA
- `Sign in` and `Create account`
- featured ready courses
- short explanation of AI-grounded learning

### Notes

Keep this page restrained. It is a trust-building front door, not a campaign site.

## Login

### Status

Current.

### Route

`/login`

### Purpose

Authenticate returning users and send them to the correct role landing.

### Key modules

- email field
- password field
- forgot password link
- create account link
- verify email link
- concise role-aware help text if needed

### Important states

- invalid credentials
- unverified account
- session refresh conflict

## Register

### Status

Current.

### Route

`/register`

### Purpose

Create a student account with minimal friction.

### Key modules

- first and last name
- email
- password
- account created confirmation
- next step guidance to verify email

### Important UX rule

Registration success must immediately explain the verify-email step.

## Verify Email

### Status

Current.

### Route

`/verify-email`

### Purpose

Complete account activation.

### Better future pattern

Support both:

- token pasted manually
- token read directly from the query string with auto-submit

## Forgot Password

### Status

Current.

### Route

`/forgot-password`

### Purpose

Start account recovery without disclosing whether an account exists.

## Reset Password

### Status

Current.

### Route

`/reset-password`

### Purpose

Set a new password and return the user toward sign-in.

## Public Catalog

### Status

Proposed public twin of the current app catalog.

### Route

`/catalog`

### Purpose

Allow browsing without account creation.

### Key modules

- search
- category and difficulty filters
- tags
- ready courses list

## Public Search

### Status

Proposed public twin of current search.

### Route

`/search`

### Purpose

Direct course discovery from query-first intent.

## Public Certificate Verification

### Status

Current route exists.

### Route

`/certificates/:certificateId`

### Purpose

Provide externally shareable proof of completion.

### Key modules

- certificate metadata
- learner name
- course title
- issued date
- certificate number
- verification note

## Notifications Center

### Status

Proposed.

### Route

`/app/notifications`

### Purpose

Act as the event inbox across learning, publishing, and admin actions.

### Key modules

- unread/all filter
- notification groups by type
- mark read
- mark all read
- preference shortcut

### Notification categories

- enrollment
- publish result
- course completion
- certificate available
- role change
- admin actions

## Profile

### Status

Current.

### Route

`/app/profile`

### Purpose

Manage personal details and role-related account actions.

### Key modules

- account summary
- personal details form
- verification state
- instructor application card for eligible users

### Future additions

- notification preferences shortcut
- password change shortcut
- linked sessions later if needed

## Settings

### Status

Proposed.

### Route

`/app/settings`

### Purpose

Separate personal profile from product preferences.

### Key modules

- notification preferences
- accessibility preferences later
- session management later
- AI data and privacy copy later

## Shared Shell Behaviors

### Global header should include

- role-aware primary nav
- quick search access
- notifications
- profile menu

### Profile menu should include

- profile
- settings
- switch mode if multi-role
- log out
