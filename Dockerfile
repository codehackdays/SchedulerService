FROM python:3.6-onbuild
CMD ["flask", "run", "-h", "0.0.0.0"]