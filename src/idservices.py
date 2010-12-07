class IDServiceFactory(object):
  pass
  

class GoogleIDService(tornado.web.RequestHandler, tornado.auth.GoogleMixin):
  @tornado.web.asynchronous
  def get(self):
    if self.get_argument("openid.mode", None):
      self.get_authenticated_user(self.async_callback(self._on_auth))
      return
    self.authenticate_redirect()

  def _on_auth(self, user):
    if not user:
      self.authenticate_redirect()
      return
    # Save the user with, e.g., set_secure_cookie()
